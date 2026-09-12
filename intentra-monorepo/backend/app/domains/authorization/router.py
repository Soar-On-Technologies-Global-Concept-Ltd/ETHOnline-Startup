"""POST /v1/transactions/{id}/authorize — a signature plus a Selfie Check create the authority (FR-5 to FR-7)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.db import sessionmaker
from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.domains.authorization import service as authorization
from app.domains.authorization.schemas import AuthorizeIn
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock

router = APIRouter(tags=["authorization"])


@router.post("/transactions/{tx_id}/authorize", summary="Approve the job and the maximum amount")
async def authorize(tx_id: uuid.UUID, body: AuthorizeIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def prepare():
        """Signature recovery and World verification happen before the row is locked: both can take a moment."""
        async with sessionmaker()() as s:
            tx, role = await load_transaction(s, tx_id, user)
            require("customer", role)
            return await authorization.verify(tx, body.signature, body.idkit_result)

    async def execute(s, prepared):
        signer, human, digest = prepared
        tx = await lock(s, tx_id)
        return await authorization.record(s, tx, user.id, body.signature, signer, digest, human)

    return await idempotent(user.id, "authorize", idempotency_key(request), body.model_dump(mode="json"), execute, prepare)
