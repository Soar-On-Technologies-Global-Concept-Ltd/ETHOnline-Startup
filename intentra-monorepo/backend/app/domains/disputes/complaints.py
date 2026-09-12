"""POST /v1/transactions/{id}/complaint — a Selfie Check, a photo, and the money freezes on-chain (FR-15)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.db import sessionmaker
from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.domains.disputes import service as disputes
from app.domains.disputes.schemas import ComplaintIn
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock

router = APIRouter(tags=["complaints"])


@router.post("/transactions/{tx_id}/complaint", summary="Report a problem with the job")
async def complaint(tx_id: uuid.UUID, body: ComplaintIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def prepare():
        async with sessionmaker()() as s:
            tx, role = await load_transaction(s, tx_id, user)
            require("customer", role)
            return await disputes.verify_complaint(tx, body.idkit_result)

    async def execute(s, human):
        tx = await lock(s, tx_id)
        return await disputes.file_complaint(s, tx, user.id, body.category.value, body.text,
                                             list(body.evidence_ids), human)

    return await idempotent(user.id, "complaint", idempotency_key(request), body.model_dump(mode="json"), execute, prepare)
