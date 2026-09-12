"""Per-transaction hash-chained audit trail (FR-20). Append only while the transaction row is locked."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.hashing import ZERO_HASH, audit_hash
from app.core.json import jsonable, utc_iso
from app.domains.audit.models import AuditEvent


def _row(ev_tx_id: str, seq: int, actor: str, event: str, from_state: str, to_state: str, payload: dict, created_at: str) -> dict:
    return {"transaction_id": ev_tx_id, "seq": seq, "actor": actor, "event": event, "from_state": from_state,
            "to_state": to_state, "payload": payload, "created_at": created_at}


async def append(s: AsyncSession, *, transaction_id: uuid.UUID, actor: str, event: str, from_state: str,
                 to_state: str, payload: dict | None = None) -> AuditEvent:
    """Takes ids and states, not a Transaction: the trail records what happened, and owns no other domain's rows."""
    last = (await s.exec(select(AuditEvent).where(AuditEvent.transaction_id == transaction_id)
                         .order_by(AuditEvent.seq.desc()).limit(1))).first()
    seq = (last.seq + 1) if last else 1
    prev = last.hash if last else ZERO_HASH
    clean = jsonable(payload or {})
    created = utc_iso()
    row = _row(str(transaction_id), seq, actor, str(event), str(from_state), str(to_state), clean, created)
    ev = AuditEvent(transaction_id=transaction_id, seq=seq, actor=actor, event=str(event), from_state=str(from_state), to_state=str(to_state),
                    payload=clean, prev_hash=prev, hash=audit_hash(prev, row), created_at=created)
    s.add(ev)
    await s.flush()
    return ev


async def events_for(s: AsyncSession, transaction_id: uuid.UUID) -> list[AuditEvent]:
    """The whole chain for one transaction, oldest first."""
    return list((await s.exec(select(AuditEvent).where(AuditEvent.transaction_id == transaction_id)
                              .order_by(AuditEvent.seq))).all())


def verify_chain(events: list[AuditEvent]) -> dict:
    prev = ZERO_HASH
    for i, ev in enumerate(sorted(events, key=lambda e: e.seq), start=1):
        row = _row(str(ev.transaction_id), ev.seq, ev.actor, ev.event, ev.from_state, ev.to_state, ev.payload, ev.created_at)
        if ev.seq != i or ev.prev_hash != prev or audit_hash(prev, row) != ev.hash:
            return {"verified": False, "checked": i - 1, "first_broken_seq": ev.seq}
        prev = ev.hash
    return {"verified": True, "checked": len(events), "first_broken_seq": None, "head_hash": prev}
