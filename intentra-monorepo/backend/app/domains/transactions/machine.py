"""The only writer of transactions.state (Blueprint §13, schematics §5.3). Callers lock the row first."""
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.audit import service as audit
from app.core.states import TERMINAL, Event, TxState, next_state
from app.core.errors import Conflict, NotFound
from app.core.columns import utcnow
from app.domains.transactions.models import Transaction


class IllegalTransition(Conflict):
    code = "illegal_transition"


async def lock(s: AsyncSession, tx_id: uuid.UUID) -> Transaction:
    tx = (await s.exec(select(Transaction).where(Transaction.id == tx_id).with_for_update())).one_or_none()
    if tx is None:
        raise NotFound("transaction not found")
    return tx


async def lock_by_key(s: AsyncSession, tx_key: str) -> Transaction | None:
    return (await s.exec(select(Transaction).where(Transaction.tx_key == tx_key.lower()).with_for_update())).one_or_none()


async def lock_by_intent_id(s: AsyncSession, intent_id: int) -> Transaction | None:
    """Chain events arrive keyed by the escrow's intentId."""
    return (await s.exec(select(Transaction).where(Transaction.escrow_intent_id == int(intent_id))
                         .with_for_update())).one_or_none()


def can(tx: Transaction, event: Event) -> bool:
    return next_state(TxState(tx.state), event) is not None


async def apply(s: AsyncSession, tx: Transaction, event: Event, actor: str, payload: dict | None = None) -> Transaction:
    to = next_state(TxState(tx.state), event)
    if to is None:
        raise IllegalTransition(f"{event} is not allowed from {tx.state}", details={"state": tx.state, "event": str(event)})
    prev = tx.state
    tx.state = to.value
    tx.version += 1
    tx.updated_at = utcnow()
    if to in TERMINAL:
        tx.closed_at = tx.updated_at
    s.add(tx)
    await audit.append(s, transaction_id=tx.id, actor=actor, event=str(event), from_state=prev,
                       to_state=to.value, payload=payload)
    return tx


async def note(s: AsyncSession, tx: Transaction, actor: str, event: str, payload: dict | None = None) -> None:
    """Audit a decision that does not change state (POLICY_BLOCKED, TX_QUEUED, EVENT_MISMATCH, ...)."""
    await audit.append(s, transaction_id=tx.id, actor=actor, event=event, from_state=tx.state,
                       to_state=tx.state, payload=payload)
