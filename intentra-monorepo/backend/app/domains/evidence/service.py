"""Upload → validate → strip EXIF → hash → store privately → anchor on Arc, in that order (schematics §13)."""
import logging
import uuid
from dataclasses import dataclass

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.hashing import sha256_hex
from app.core.states import Event, EvidenceKind, TxState
from app.core.errors import Forbidden, Unprocessable
from app.core.logging import log
from app.domains.evidence.models import Evidence
from app.domains.transactions.models import Transaction
from app.domains.payments import resolver
from app.integrations.arc import client as arc_client
from app.domains.evidence.sanitize import sanitize
from app.integrations.storage import LocalStorage, storage
from app.domains.transactions import machine

logger = logging.getLogger("evidence")

RULES = {
    EvidenceKind.AFTER_PHOTO: ("provider", {TxState.IN_PROGRESS, TxState.EVIDENCE_SUBMITTED}),
    EvidenceKind.COMPLAINT: ("customer", {TxState.DELIVERED}),
    EvidenceKind.COUNTER: ("provider", {TxState.DISPUTED}),
}


@dataclass(frozen=True)
class StoredFile:
    sha256: str
    storage_uri: str
    mime: str
    size: int


def check_allowed(kind: EvidenceKind, role: str, state: str, scope_item: str | None, checklist: list[str]) -> None:
    expected_role, states = RULES[kind]
    if role != expected_role:
        raise Forbidden(f"only the {expected_role} can upload {kind.value} evidence", code="wrong_role")
    if TxState(state) not in states:
        raise machine.IllegalTransition(f"{kind.value} evidence is not accepted while the job is {state}", details={"state": state})
    if kind is EvidenceKind.AFTER_PHOTO:
        if scope_item is None:
            raise Unprocessable("say which item this photo covers", code="validation_error", details={"expected": checklist})
        if checklist and scope_item not in checklist:
            raise Unprocessable(f"{scope_item} is not part of the agreed scope", code="validation_error", details={"expected": checklist})


async def store(raw: bytes, tx_id: uuid.UUID) -> StoredFile:
    """Runs before the database transaction: sanitising and uploading can take a moment."""
    clean, mime, ext = sanitize(raw)
    digest = sha256_hex(clean)
    uri = await storage().put(f"{tx_id}/{digest[2:]}.{ext}", clean, mime)
    return StoredFile(digest, uri, mime, len(clean))


async def record(s: AsyncSession, tx: Transaction, user_id: uuid.UUID, role: str, kind: EvidenceKind,
                 scope_item: str | None, caption: str | None, file: StoredFile) -> tuple[Evidence, bool]:
    """Insert the evidence row, queue its anchor and move the state on the first after-photo. Re-uploading the same file is a no-op."""
    existing = (await s.exec(select(Evidence).where(Evidence.transaction_id == tx.id, Evidence.sha256 == file.sha256))).one_or_none()
    if existing is not None:
        return existing, False
    row = Evidence(transaction_id=tx.id, submitted_by=user_id, role=role, kind=kind.value, scope_item=scope_item,
                   sha256=file.sha256, storage_uri=file.storage_uri, mime=file.mime, bytes=file.size, caption=caption)
    s.add(row)
    await s.flush()
    queued = await resolver.queue_anchor(s, tx.id, tx.tx_key, file.sha256)
    row.anchor_tx_id = queued.id
    s.add(row)
    payload = {"evidence_id": str(row.id), "kind": kind.value, "scope_item": scope_item, "sha256": file.sha256}
    if kind is EvidenceKind.AFTER_PHOTO and tx.state == TxState.IN_PROGRESS.value:
        await machine.apply(s, tx, Event.EVIDENCE_ADDED, f"provider:{user_id}", payload)
    else:
        await machine.note(s, tx, f"{role}:{user_id}", "EVIDENCE_ADDED", payload)
    log(logger, "evidence stored", kind=kind.value, scope_item=scope_item, sha256=file.sha256, anchor_id=queued.id)
    return row, True


async def rows(s: AsyncSession, tx_id: uuid.UUID) -> list[Evidence]:
    return list((await s.exec(select(Evidence).where(Evidence.transaction_id == tx_id).order_by(Evidence.created_at))).all())


def catalog(items: list[Evidence]) -> list[dict]:
    """Minimal context for the model: no addresses, no names, no other transactions."""
    return [{"id": str(e.id), "kind": e.kind, "by": e.role, "scope_item": e.scope_item, "caption": e.caption or ""} for e in items]


async def visible(items: list[Evidence]) -> list[dict]:
    out = []
    for e in items:
        out.append({"id": str(e.id), "kind": e.kind, "role": e.role, "scope_item": e.scope_item, "caption": e.caption,
                    "sha256": e.sha256, "mime": e.mime, "bytes": e.bytes, "created_at": e.created_at,
                    "url": await storage().signed_url(e.storage_uri),
                    "anchored_tx_url": arc_client.explorer_tx(e.anchored_tx),
                    "anchoring": "ANCHORED" if e.anchored_tx else "QUEUED"})
    return out


def missing_items(checklist: list[str], items: list[Evidence]) -> list[str]:
    covered = {e.scope_item for e in items if e.kind == EvidenceKind.AFTER_PHOTO.value and e.scope_item}
    return [item for item in checklist if item not in covered]


async def mark_anchored(s: AsyncSession, transaction_id: uuid.UUID, evidence_hash: str, tx_hash: str) -> bool:
    """The escrow published the hash: link the proof. Returns False if the hash is not evidence of this transaction."""
    row = (await s.exec(select(Evidence).where(Evidence.transaction_id == transaction_id,
                                               Evidence.sha256 == evidence_hash.lower()))).one_or_none()
    if row is None:
        return False
    row.anchored_tx = tx_hash
    s.add(row)
    return True


def read_signed_file(key: str, exp: int, sig: str) -> bytes | None:
    """Local-storage counterpart of a presigned URL. Returns None for an expired or forged link."""
    store = storage()
    if not isinstance(store, LocalStorage):
        return None
    return store.read_verified(key, exp, sig)


async def unanchored(s: AsyncSession, transaction_id: uuid.UUID | None = None) -> list[Evidence]:
    """Stored, hashed, but not yet proven on-chain."""
    query = select(Evidence).where(Evidence.anchored_tx.is_(None), Evidence.anchor_tx_id.is_not(None))
    if transaction_id is not None:
        query = query.where(Evidence.transaction_id == transaction_id)
    return list((await s.exec(query)).all())


async def set_anchor_tx(s: AsyncSession, evidence_id: uuid.UUID, chain_tx_id: int) -> None:
    row = await s.get(Evidence, evidence_id)
    if row is not None:
        row.anchor_tx_id = chain_tx_id
        s.add(row)
