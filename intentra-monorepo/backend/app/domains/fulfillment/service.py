"""The work itself: what was promised, what the photos cover, and the deliverable hash that goes on-chain."""
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.errors import Unprocessable
from app.core.hashing import deliverable_hash
from app.core.states import Event, EvidenceKind
from app.domains.evidence import service as evidence
from app.domains.fulfillment.models import Fulfillment
from app.domains.transactions import machine
from app.integrations.arc import client as arc_client


async def for_transaction(s: AsyncSession, transaction_id: uuid.UUID) -> Fulfillment | None:
    return (await s.exec(select(Fulfillment).where(Fulfillment.transaction_id == transaction_id))).one_or_none()


async def ensure(s: AsyncSession, transaction_id: uuid.UUID, checklist_items: list[str]) -> Fulfillment:
    """Created when the escrow confirms funding, so the provider has a checklist the moment they can start."""
    row = await for_transaction(s, transaction_id)
    if row is None:
        row = Fulfillment(transaction_id=transaction_id, checklist={"items": list(checklist_items)}, coverage={})
        s.add(row)
        await s.flush()
    return row


async def checklist(s: AsyncSession, transaction_id: uuid.UUID) -> list[str]:
    row = await for_transaction(s, transaction_id)
    return list((row.checklist or {}).get("items", []) if row else [])


async def cover(s: AsyncSession, transaction_id: uuid.UUID, scope_item: str | None) -> None:
    """One more photo against a checklist item."""
    row = await for_transaction(s, transaction_id)
    if row is None or scope_item is None:
        return
    coverage = dict(row.coverage or {})
    coverage[scope_item] = int(coverage.get(scope_item, 0)) + 1
    row.coverage = coverage
    row.status = "IN_PROGRESS" if row.status == "NOT_STARTED" else row.status
    row.updated_at = utcnow()
    s.add(row)


async def start(s: AsyncSession, tx, user_id: uuid.UUID) -> tuple[int, dict]:
    row = await for_transaction(s, tx.id)
    if row is not None:
        row.status, row.started_at, row.updated_at = "IN_PROGRESS", utcnow(), utcnow()
        s.add(row)
    await machine.apply(s, tx, Event.WORK_STARTED, f"provider:{user_id}", {"started_at": utcnow()})
    return 200, {"transaction": {"id": str(tx.id), "state": tx.state}, "checklist": await checklist(s, tx.id)}


async def deliver_call(s: AsyncSession, tx, user_id: uuid.UUID) -> tuple[int, dict]:
    """Every room needs an after-photo before the provider can mark the job delivered."""
    items = await evidence.rows(s, tx.id)
    expected = await checklist(s, tx.id)
    missing = evidence.missing_items(expected, items)
    if missing:
        raise Unprocessable("add an after-photo for every room before marking the job delivered",
                            code="insufficient_evidence", details={"missing": missing})
    photos = [e.sha256 for e in items if e.kind == EvidenceKind.AFTER_PHOTO.value]
    digest = deliverable_hash(photos)
    row = await for_transaction(s, tx.id)
    if row is not None:
        row.deliverable_hash, row.updated_at = digest, utcnow()
        s.add(row)
    await machine.note(s, tx, f"provider:{user_id}", "DELIVERABLE_BUILT", {"deliverable_hash": digest, "photos": len(photos)})
    return 200, {"call": arc_client.call(get_settings().escrow_address, "submit", [tx.tx_key, digest]),
                 "deliverable_hash": digest, "transaction": {"id": str(tx.id), "state": tx.state}}


async def expected_deliverable(s: AsyncSession, transaction_id: uuid.UUID) -> str | None:
    row = await for_transaction(s, transaction_id)
    return row.deliverable_hash if row else None


async def mark_delivered(s: AsyncSession, transaction_id: uuid.UUID, submit_tx: str, when) -> None:
    """Called when the escrow's Submitted event lands, never from a request."""
    row = await for_transaction(s, transaction_id)
    if row is not None:
        row.status, row.submit_tx, row.delivered_at, row.updated_at = "DELIVERED", submit_tx, when, utcnow()
        s.add(row)


async def view(s: AsyncSession, transaction_id: uuid.UUID, items: list) -> dict:
    row = await for_transaction(s, transaction_id)
    expected = list((row.checklist or {}).get("items", []) if row else [])
    return {"items": expected, "coverage": (row.coverage or {}) if row else {},
            "missing": evidence.missing_items(expected, items)}
