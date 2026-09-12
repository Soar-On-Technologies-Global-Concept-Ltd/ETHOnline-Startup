"""Money and the chain. FastAPI is not the bank: this domain returns call data for the customer's wallet, records what
the wallet reported, and reads back what the escrow actually did. State only ever commits on a confirmed event.
"""
import uuid
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.errors import Conflict
from app.core.states import Event, TxState
from app.domains.authorization import service as authorization
from app.domains.intents import service as intents
from app.domains.payments.models import BlockchainEvent, ChainTx, Payment
from app.domains.transactions import machine
from app.domains.transactions import policy as tx_policy
from app.integrations.arc import client as arc_client


async def record(s: AsyncSession, transaction_id: uuid.UUID, direction: str, external_ref: str, amount_minor: int | None,
                 status: str = "CONFIRMED") -> None:
    """One row per (rail, direction, reference), so a replayed event cannot double-count money."""
    row = (await s.exec(select(Payment).where(Payment.rail == "arc", Payment.direction == direction,
                                              Payment.external_ref == external_ref))).one_or_none()
    if row is None:
        row = Payment(transaction_id=transaction_id, rail="arc", direction=direction, external_ref=external_ref,
                      status=status, amount_minor=amount_minor)
    row.status, row.amount_minor, row.updated_at = status, amount_minor, utcnow()
    s.add(row)


async def has_pending_funding(s: AsyncSession, transaction_id: uuid.UUID) -> bool:
    return (await s.exec(select(Payment).where(Payment.transaction_id == transaction_id, Payment.direction == "FUND",
                                               Payment.status == "PENDING"))).first() is not None


async def payments_for(s: AsyncSession, transaction_id: uuid.UUID) -> list[dict]:
    rows = (await s.exec(select(Payment).where(Payment.transaction_id == transaction_id)
                         .order_by(Payment.created_at))).all()
    return [{"direction": p.direction, "status": p.status, "amount_minor": p.amount_minor,
             "explorer_url": arc_client.explorer_tx(p.external_ref.split(":")[0])} for p in rows]


async def pending_for(s: AsyncSession, transaction_id: uuid.UUID) -> dict | None:
    """What the UI shows as \"confirming…\" between the request and the escrow event."""
    row = (await s.exec(select(ChainTx).where(ChainTx.transaction_id == transaction_id,
                                              ChainTx.status.in_(["QUEUED", "SENT"]))
                        .order_by(ChainTx.id.desc()).limit(1))).first()
    if row is not None:
        return {"kind": row.kind, "status": row.status, "tx_hash": row.tx_hash,
                "explorer_url": arc_client.explorer_tx(row.tx_hash)}
    payment = (await s.exec(select(Payment).where(Payment.transaction_id == transaction_id, Payment.status == "PENDING")
                            .order_by(Payment.created_at.desc()).limit(1))).first()
    if payment is None:
        return None
    return {"kind": payment.direction, "status": "PENDING", "tx_hash": payment.external_ref,
            "explorer_url": arc_client.explorer_tx(payment.external_ref)}


async def fund_calls(s: AsyncSession, tx, user_id: uuid.UUID, provider_wallet: str) -> tuple[int, dict]:
    """Policy runs before funding; the API hands back call data and never sends a user transaction itself."""
    from app.domains.transactions import service as transactions

    settings = get_settings()
    auth = await authorization.latest(s, tx.id)
    if auth is None:
        raise Conflict("approve the job before funding it", code="no_authorization")
    quote = await intents.quote_view(s, tx.quote_id)
    await tx_policy.enforce(tx, f"customer:{user_id}",
                            tx_policy.Action(kind="fund", state=tx.state, currency=tx.currency,
                                             amount_minor=int(tx.amount_minor or 0), provider_verified=True,
                                             provider_address=provider_wallet,
                                             scope_hash=quote["scope_hash"] if quote else None),
                            tx_policy.context(tx, await authorization.view(s, tx.id)))
    if tx.state == TxState.AUTHORIZED.value:
        expires_ts = int(utcnow().timestamp()) + settings.delivery_deadline_seconds
        tx.dispute_window_s = settings.dispute_window_seconds
        tx.expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc)
        await machine.apply(s, tx, Event.FUNDING_STARTED, f"customer:{user_id}",
                            {"amount_minor": tx.amount_minor, "dispute_window_s": tx.dispute_window_s,
                             "expires_at": tx.expires_at})
    amount = str(int(tx.amount_minor or 0))
    escrow = arc_client.checksum(settings.escrow_address)
    calls = [arc_client.call(settings.usdc_address, "approve", [escrow, amount]),
             arc_client.call(settings.escrow_address, "fund",
                             [tx.tx_key, arc_client.checksum(provider_wallet), amount, auth.authorization_hash,
                              int(tx.dispute_window_s), int(tx.expires_at.timestamp())])]
    return 200, {"calls": calls, "transaction": {"id": str(tx.id), "state": tx.state},
                 "amount": transactions.amount_view(tx)}


async def release_call(s: AsyncSession, tx, user_id: uuid.UUID) -> tuple[int, dict]:
    await tx_policy.enforce(tx, f"customer:{user_id}",
                            tx_policy.Action(kind="release", state=tx.state, currency=tx.currency,
                                             amount_minor=int(tx.amount_minor or 0)),
                            tx_policy.context(tx, await authorization.view(s, tx.id)))
    await machine.note(s, tx, f"customer:{user_id}", "RELEASE_REQUESTED", {"amount_minor": tx.amount_minor})
    return 200, {"call": arc_client.call(get_settings().escrow_address, "release", [tx.tx_key]),
                 "transaction": {"id": str(tx.id), "state": tx.state}}


async def report_chain_tx(s: AsyncSession, tx, user_id: uuid.UUID, direction: str, tx_hash: str) -> tuple[int, dict]:
    """A hint from the wallet so the receipt can be fetched early. The state still commits only on the event."""
    tx_hash = tx_hash.lower()
    existing = (await s.exec(select(Payment).where(Payment.rail == "arc", Payment.direction == direction,
                                                   Payment.external_ref == tx_hash))).one_or_none()
    if existing is None:
        s.add(Payment(transaction_id=tx.id, rail="arc", direction=direction, external_ref=tx_hash, status="PENDING",
                      amount_minor=tx.amount_minor))
        await machine.note(s, tx, f"customer:{user_id}", "TX_REPORTED", {"direction": direction, "tx_hash": tx_hash})
    return 202, {"payment": {"status": "PENDING", "tx_hash": tx_hash, "explorer_url": arc_client.explorer_tx(tx_hash)},
                 "transaction": {"id": str(tx.id), "state": tx.state}}


async def has_release_queued(s: AsyncSession, transaction_id: uuid.UUID) -> bool:
    return (await s.exec(select(ChainTx).where(ChainTx.transaction_id == transaction_id, ChainTx.kind == "RELEASE",
                                               ChainTx.status.in_(["QUEUED", "SENT", "MINED"])))).first() is not None


async def anchor_state(s: AsyncSession, chain_tx_id: int | None) -> str | None:
    row = None if chain_tx_id is None else await s.get(ChainTx, chain_tx_id)
    return row.status if row else None


async def anchor_attempts(s: AsyncSession, transaction_id: uuid.UUID, evidence_hash: str) -> int:
    rows = (await s.exec(select(ChainTx).where(ChainTx.transaction_id == transaction_id, ChainTx.kind == "ANCHOR"))).all()
    return sum(1 for row in rows if (row.args or {}).get("evidence_hash") == evidence_hash)


# ---------------------------------------------------------------- the escrow log this domain has already seen

async def record_event(s: AsyncSession, *, name: str, tx_hash: str, log_index: int, block_number: int, contract: str,
                       tx_key: str | None, payload: dict) -> bool:
    """Insert-first dedupe on (tx_hash, log_index). False means the log was already handled, so a replay does nothing."""
    if await s.get(BlockchainEvent, (tx_hash, log_index)) is not None:
        return False
    s.add(BlockchainEvent(tx_hash=tx_hash, log_index=log_index, block_number=block_number, contract=contract,
                          name=name, tx_key=tx_key, payload=payload))
    await s.flush()
    return True


async def mark_event(s: AsyncSession, tx_hash: str, log_index: int, *, handled: bool, error: str | None) -> None:
    row = await s.get(BlockchainEvent, (tx_hash, log_index))
    if row is not None:
        row.handled, row.handle_error = handled, error
        s.add(row)


async def outbox_counts(s: AsyncSession) -> dict[str, int]:
    """What /healthz reports: how much resolver work is queued, in flight or stuck."""
    from sqlmodel import func

    rows = (await s.exec(select(ChainTx.status, func.count()).group_by(ChainTx.status))).all()
    return {status.lower(): int(count) for status, count in rows}
