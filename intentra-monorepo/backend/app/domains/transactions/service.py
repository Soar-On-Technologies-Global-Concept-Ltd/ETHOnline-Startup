"""The aggregate root. A transaction is opened with the intent, bound to a quote, and closed by the chain.

This module owns the transaction row and nothing else: it takes plain values from other domains rather than their rows,
and anything that needs several domains at once lives in app/orchestration.
"""
import logging
import secrets
import uuid
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.errors import Conflict, NotFound
from app.core.money import kobo_to_micro_usdc
from app.core.states import Event, TxState
from app.domains.authorization import service as authorization
from app.domains.transactions import machine
from app.domains.transactions import policy as tx_policy
from app.domains.transactions.models import Transaction
from app.integrations.arc import eip712

logger = logging.getLogger("transactions")

ACTIONS = {
    TxState.CREATED: {"customer": ["describe_job"]},
    TxState.INTENT_STRUCTURED: {"customer": ["select_quote", "cancel"]},
    TxState.QUOTE_SELECTED: {"customer": ["authorize", "cancel"]},
    TxState.AWAITING_AUTHORIZATION: {"customer": ["authorize", "cancel"]},
    TxState.AUTHORIZED: {"customer": ["fund", "cancel"]},
    TxState.FUNDING: {"customer": ["fund"]},
    TxState.FUNDED: {"provider": ["start"]},
    TxState.IN_PROGRESS: {"provider": ["upload_evidence", "deliver"]},
    TxState.EVIDENCE_SUBMITTED: {"provider": ["upload_evidence", "deliver"]},
    TxState.DELIVERED: {"customer": ["release", "complaint", "upload_evidence"]},
    TxState.DISPUTED: {"provider": ["respond", "upload_evidence"]},
    TxState.RESOLVING: {},
    TxState.PROPOSED: {"customer": ["accept", "reject"], "provider": ["accept", "reject"]},
}


def new_tx_key() -> str:
    """32 random bytes: nobody can predict the escrow slot and take it first."""
    return "0x" + secrets.token_hex(32)


def allowed_actions(tx: Transaction, role: str) -> list[str]:
    """Computed here so the frontend never re-implements the state machine to decide which buttons to show."""
    return list(ACTIONS.get(TxState(tx.state), {}).get(role, []))


def amount_view(tx: Transaction) -> dict:
    return {"minor": tx.amount_minor, "currency": tx.currency, "display_minor": tx.display_amount_minor,
            "display_currency": "NGN", "fx_rate": tx.fx_rate_ngn_per_usdc, "fx_label": "demo rate"}


async def get(s: AsyncSession, transaction_id: uuid.UUID) -> Transaction:
    tx = await s.get(Transaction, transaction_id)
    if tx is None:
        raise NotFound("transaction not found")
    return tx


async def by_intent(s: AsyncSession, intent_id: uuid.UUID) -> Transaction:
    """The read counterpart of by_intent_locked: a screen refresh must not take a row lock the workers wait on."""
    tx = (await s.exec(select(Transaction).where(Transaction.intent_id == intent_id))).one_or_none()
    if tx is None:
        raise NotFound("request not found")
    return tx


async def by_intent_locked(s: AsyncSession, intent_id: uuid.UUID) -> Transaction:
    tx = (await s.exec(select(Transaction).where(Transaction.intent_id == intent_id).with_for_update())).one_or_none()
    if tx is None:
        raise NotFound("request not found")
    return tx


async def open_for_intent(s: AsyncSession, customer_id: uuid.UUID, intent_id: uuid.UUID, spec: dict | None,
                          model: str | None) -> Transaction:
    """Every request gets a transaction immediately, so there is one place to hang the audit trail from."""
    tx = Transaction(tx_key=new_tx_key(), intent_id=intent_id, customer_id=customer_id, state=TxState.CREATED.value)
    s.add(tx)
    await s.flush()
    await machine.note(s, tx, f"customer:{customer_id}", "TRANSACTION_CREATED", {"intent_id": str(intent_id)})
    if spec:
        await machine.apply(s, tx, Event.INTENT_STRUCTURED, f"customer:{customer_id}",
                            {"intent_id": str(intent_id), "spec": spec, "model": model})
    return tx


async def select_quote(s: AsyncSession, tx: Transaction, customer_id: uuid.UUID, quote: dict, provider: dict,
                       customer_wallet: str, provider_wallet: str) -> tuple[int, dict]:
    """Bind the offer, freeze the rate, and issue the authorization the customer will sign — in one request."""
    settings = get_settings()
    actor = f"customer:{customer_id}"
    if quote["intent_id"] != str(tx.intent_id):
        raise NotFound("that quote is not part of this request")
    if quote["expires_at"] <= utcnow():
        raise Conflict("this quote has expired; refresh the recommendations", code="quote_expired")
    rate = settings.demo_fx_rate_ngn_per_usdc
    amount_minor = kobo_to_micro_usdc(quote["amount_minor"], rate)

    await tx_policy.enforce(tx, actor,
                            tx_policy.Action(kind="quote_select", state=tx.state, currency=tx.currency,
                                             amount_minor=amount_minor, provider_verified=provider["verified"],
                                             provider_address=provider_wallet, scope_hash=quote["scope_hash"]),
                            tx_policy.context(tx))
    tx.quote_id, tx.provider_id = uuid.UUID(quote["id"]), uuid.UUID(str(provider["id"]))
    tx.amount_minor, tx.display_amount_minor, tx.fx_rate_ngn_per_usdc = amount_minor, quote["amount_minor"], rate
    await machine.apply(s, tx, Event.QUOTE_SELECTED, actor,
                        {"quote_id": quote["id"], "provider_id": str(provider["id"]), "amount_minor": amount_minor,
                         "display_amount_minor": quote["amount_minor"], "fx_rate": rate, "scope_hash": quote["scope_hash"]})

    # Policy again with the candidate authorization, before any typed data is offered.
    await tx_policy.enforce(tx, actor,
                            tx_policy.Action(kind="authorize", state=TxState.AWAITING_AUTHORIZATION.value,
                                             currency=tx.currency, amount_minor=amount_minor,
                                             provider_verified=provider["verified"], provider_address=provider_wallet,
                                             scope_hash=quote["scope_hash"], human_check_ok=True),
                            tx_policy.context(tx))
    offer = authorization.build_offer(tx.tx_key, customer_wallet, provider_wallet, amount_minor, quote["scope"],
                                      quote["scope_hash"])
    tx.authorization_offer = offer
    tx.expires_at = datetime.fromisoformat(offer["expires_at"])
    await machine.apply(s, tx, Event.AUTHORIZATION_ISSUED, "system:api",
                        {"authorization_hash": offer["digest"], "expires_at": tx.expires_at,
                         "max_amount_minor": amount_minor})
    return 201, {"transaction": {"id": str(tx.id), "tx_key": tx.tx_key, "state": tx.state},
                 "authorization_typed_data": eip712.for_client(offer["typed_data"]),
                 "human_check": {"action": settings.world_action_authorize, "signal": tx.tx_key},
                 "amount": amount_view(tx), "scope": quote["scope"], "expires_at": tx.expires_at}


async def cancel(s: AsyncSession, tx: Transaction, customer_id: uuid.UUID, reason: str | None,
                 funding_pending: bool) -> tuple[int, dict]:
    """Only before money moves, and never while a funding transaction is still confirming."""
    if funding_pending:
        raise Conflict("a funding transaction is still confirming; wait for it to settle", code="funding_pending")
    tx.close_reason = reason or "declined"
    await machine.apply(s, tx, Event.DECLINED, f"customer:{customer_id}", {"reason": tx.close_reason})
    return 200, {"transaction": {"id": str(tx.id), "state": tx.state, "close_reason": tx.close_reason}}


async def mark_funded(s: AsyncSession, tx: Transaction, when: datetime) -> None:
    tx.funded_at = when


async def mark_delivered(s: AsyncSession, tx: Transaction, release_after: datetime) -> None:
    tx.release_after, tx.delivered_at = release_after, utcnow()


async def due_for_release(s: AsyncSession, now: datetime) -> list[uuid.UUID]:
    """Delivered, past the window on the chain's clock, and not yet released."""
    return list((await s.exec(select(Transaction.id).where(Transaction.state == TxState.DELIVERED.value,
                                                           Transaction.release_after.is_not(None),
                                                           Transaction.release_after <= now))).all())


async def in_states(s: AsyncSession, states: list[str]) -> list[uuid.UUID]:
    return list((await s.exec(select(Transaction.id).where(Transaction.state.in_(states)))).all())


# ---------------------------------------------------------------- the escrow's own identifier

async def by_intent_id(s: AsyncSession, intent_id: int) -> Transaction | None:
    """Everything on-chain is keyed by the escrow's auto-incrementing intentId, not by our tx_key."""
    return (await s.exec(select(Transaction).where(Transaction.escrow_intent_id == int(intent_id)))).one_or_none()


async def bind_intent_id(s: AsyncSession, tx: Transaction, intent_id: int) -> None:
    tx.escrow_intent_id = int(intent_id)
    s.add(tx)


async def funded_since_before(s: AsyncSession, cutoff: datetime) -> list[uuid.UUID]:
    """Jobs the escrow still holds money for, funded before the cutoff and not yet closed."""
    live = [TxState.FUNDED.value, TxState.IN_PROGRESS.value, TxState.EVIDENCE_SUBMITTED.value,
            TxState.DELIVERED.value, TxState.DISPUTED.value, TxState.RESOLVING.value, TxState.PROPOSED.value]
    return list((await s.exec(select(Transaction.id).where(Transaction.state.in_(live),
                                                           Transaction.funded_at.is_not(None),
                                                           Transaction.funded_at <= cutoff))).all())
