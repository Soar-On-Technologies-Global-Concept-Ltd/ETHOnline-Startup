"""Permission. The API builds the typed data, the customer signs it, and only then does authority exist.

AI can prepare a transaction; it cannot create authority. That is this domain's whole job.
"""
import uuid
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, Gone
from app.core.states import Event
from app.domains.authorization.models import Authorization
from app.domains.identity import service as identity
from app.domains.transactions import machine
from app.domains.transactions import policy as tx_policy
from app.integrations.arc import eip712


async def latest(s: AsyncSession, transaction_id: uuid.UUID) -> Authorization | None:
    return (await s.exec(select(Authorization).where(Authorization.transaction_id == transaction_id)
                         .order_by(Authorization.version.desc()).limit(1))).first()


async def view(s: AsyncSession, transaction_id: uuid.UUID) -> tx_policy.AuthorizationView | None:
    """What policy needs to know about the standing authority, without handing over the row."""
    row = await latest(s, transaction_id)
    if row is None:
        return None
    return tx_policy.AuthorizationView(row.max_amount_minor, row.provider_address, row.scope_hash, row.expires_at)


def build_offer(tx_key: str, customer_wallet: str, provider_wallet: str, amount_minor: int, scope: dict,
                scope_hash: str) -> dict:
    """The typed data the customer will sign. Built and stored by the API so the browser cannot sign something else."""
    expires_at = utcnow() + timedelta(seconds=get_settings().authorization_ttl_seconds)
    typed = eip712.authorization_typed_data(tx_key, customer_wallet, provider_wallet, amount_minor, scope_hash,
                                            int(expires_at.timestamp()))
    return {"typed_data": typed, "scope": scope, "scope_hash": scope_hash, "max_amount_minor": amount_minor,
            "provider_address": provider_wallet.lower(), "customer_address": customer_wallet.lower(),
            "expires_at": expires_at.isoformat(), "issued_at": utcnow().isoformat(),
            "digest": eip712.struct_hash(typed)}


async def verify(tx, signature: str, idkit_result: dict):
    """Signature recovery and World verification, both before the row is locked: they take a moment."""
    offer = tx.authorization_offer or {}
    if not offer:
        raise Conflict("there is nothing to approve yet", code="no_authorization")
    try:
        signer = eip712.recover(offer["typed_data"], signature)
    except Exception as err:
        raise Forbidden("that signature could not be read", code="signature_mismatch") from err
    human = await identity.verify_human(idkit_result, action=get_settings().world_action_authorize, signal=tx.tx_key)
    return signer, human, offer.get("digest")


async def record(s: AsyncSession, tx, user_id: uuid.UUID, signature: str, signer: str, digest: str,
                 human) -> tuple[int, dict]:
    """Insert the authority and move the transaction to AUTHORIZED, with the row already locked."""
    settings = get_settings()
    offer = tx.authorization_offer or {}
    if tx.state != machine.TxState.AWAITING_AUTHORIZATION.value:
        raise machine.IllegalTransition(f"this job is {tx.state}, so it cannot be approved now", details={"state": tx.state})
    if offer.get("digest") != digest:
        raise Conflict("the job changed while you were approving it; review it again", code="authorization_stale")
    expires_at = datetime.fromisoformat(offer["expires_at"])
    if expires_at <= utcnow():
        raise Gone("this approval expired; review the job and approve again", code="authorization_expired")
    wallet = await identity.wallet_of(s, user_id)
    if wallet is None or signer != wallet.lower():
        raise Forbidden("that signature does not match your wallet", code="signature_mismatch")

    await tx_policy.enforce(tx, f"customer:{user_id}",
                            tx_policy.Action(kind="authorize", state=tx.state, currency=tx.currency,
                                             amount_minor=int(tx.amount_minor or 0), provider_verified=True,
                                             provider_address=offer["provider_address"], scope_hash=offer["scope_hash"],
                                             human_check_ok=human is not None),
                            tx_policy.context(tx))
    check_id = await identity.record_human_check(s, user_id=user_id, transaction_id=tx.id,
                                                 action=settings.world_action_authorize, verified=human,
                                                 scope_key=str(tx.id))
    await machine.note(s, tx, f"customer:{user_id}", "HUMAN_CHECK_VERIFIED",
                       {"action": settings.world_action_authorize, "human_check_id": str(check_id)})
    previous = await latest(s, tx.id)
    row = Authorization(transaction_id=tx.id, version=(previous.version + 1) if previous else 1,
                        typed_data=offer["typed_data"], signature=signature, signer=signer, authorization_hash=digest,
                        max_amount_minor=int(offer["max_amount_minor"]), scope_hash=offer["scope_hash"],
                        provider_address=offer["provider_address"], expires_at=expires_at, human_check_id=check_id,
                        policy_decision={"decision": "ALLOW", "reasons": []})
    s.add(row)
    await identity.mark_wallet_verified(s, user_id)
    await machine.apply(s, tx, Event.AUTHORIZED, f"customer:{user_id}",
                        {"authorization_id": str(row.id), "authorization_hash": digest,
                         "max_amount_minor": row.max_amount_minor, "expires_at": expires_at})
    return 200, {"transaction": {"id": str(tx.id), "state": tx.state},
                 "authorization": {"id": str(row.id), "authorization_hash": digest, "expires_at": expires_at}}
