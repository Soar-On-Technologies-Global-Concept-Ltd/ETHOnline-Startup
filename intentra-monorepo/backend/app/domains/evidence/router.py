"""Evidence upload, listing, and the signed-URL file route (FR-11, FR-16)."""
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db import session_scope, sessionmaker
from app.core.errors import NotFound, PayloadTooLarge, Unprocessable
from app.core.states import EvidenceKind
from app.domains.evidence import service as evidence
from app.domains.fulfillment import service as fulfillment
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.transactions.deps import load_transaction
from app.domains.transactions.machine import lock

router = APIRouter(tags=["evidence"])
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    chunks, total = [], 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > limit:
            raise PayloadTooLarge(f"the file is larger than {limit // (1024 * 1024)} MB")
        chunks.append(chunk)
    if not chunks:
        raise Unprocessable("the file is empty", code="validation_error")
    return b"".join(chunks)


@router.post("/transactions/{tx_id}/evidence", summary="Upload a photo as evidence")
async def upload(tx_id: uuid.UUID, file: UploadFile = File(...), kind: str = Form(...),
                 scope_item: str | None = Form(default=None), caption: str | None = Form(default=None),
                 user: CurrentUser = Depends(current_user)):
    try:
        parsed_kind = EvidenceKind(kind)
    except ValueError as err:
        raise Unprocessable(f"{kind} is not an evidence kind", code="validation_error",
                            details={"expected": [k.value for k in EvidenceKind]}) from err
    raw = await _read_limited(file, get_settings().max_upload_bytes)
    async with sessionmaker()() as s:
        tx, role = await load_transaction(s, tx_id, user)
        evidence.check_allowed(parsed_kind, role, tx.state, scope_item, await fulfillment.checklist(s, tx_id))
    stored = await evidence.store(raw, tx_id)           # sanitise and upload outside the transaction
    async with session_scope() as s:
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        checklist = await fulfillment.checklist(s, tx_id)
        evidence.check_allowed(parsed_kind, role, tx.state, scope_item, checklist)
        row, created = await evidence.record(s, tx, user.id, role, parsed_kind, scope_item, caption, stored)
        if created and parsed_kind is EvidenceKind.AFTER_PHOTO:
            await fulfillment.cover(s, tx.id, scope_item)
        body = {"evidence": {"id": str(row.id), "kind": row.kind, "scope_item": row.scope_item, "sha256": row.sha256,
                             "bytes": row.bytes, "mime": row.mime,
                             "anchoring": "ANCHORED" if row.anchored_tx else "QUEUED"},
                "transaction": {"id": str(tx.id), "state": tx.state},
                "missing": evidence.missing_items(checklist, await evidence.rows(s, tx.id))}
    return JSONResponse(status_code=201 if created else 200, content=jsonable_encoder(body))


@router.get("/transactions/{tx_id}/evidence", summary="List the evidence, with short-lived links")
async def listing(tx_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        tx, _ = await load_transaction(s, tx_id, user)
        items = await evidence.rows(s, tx.id)
        checklist = await fulfillment.checklist(s, tx.id)
        return {"items": await evidence.visible(items), "checklist": checklist,
                "missing": evidence.missing_items(checklist, items)}


@router.get("/files/{key:path}", include_in_schema=False)
async def signed_file(key: str, exp: int = Query(...), sig: str = Query(...)) -> Response:
    """The link itself carries the proof, so no bearer token is needed."""
    data = evidence.read_signed_file(key, exp, sig)
    if data is None:
        raise NotFound("this link has expired")
    return Response(content=data, media_type=MEDIA.get(PurePosixPath(key).suffix.lower(), "application/octet-stream"),
                    headers={"Cache-Control": "private, max-age=60"})
