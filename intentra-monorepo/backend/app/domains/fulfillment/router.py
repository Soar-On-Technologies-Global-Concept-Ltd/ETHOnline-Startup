"""Start the job, then mark it delivered (FR-11, FR-12)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.core.schemas import ChainReportIn
from app.domains.fulfillment import service as fulfillment
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.payments import service as payments
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock

router = APIRouter(tags=["fulfillment"])


@router.post("/transactions/{tx_id}/start", summary="Start the job once the money is locked")
async def start(tx_id: uuid.UUID, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        require("provider", role)
        return await fulfillment.start(s, tx, user.id)

    return await idempotent(user.id, "start", idempotency_key(request, required=False), {}, execute)


@router.post("/transactions/{tx_id}/deliver", summary="Mark the job delivered and get the submit call")
async def deliver(tx_id: uuid.UUID, body: ChainReportIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        require("provider", role)
        if body.tx_hash:
            return await payments.report_chain_tx(s, tx, user.id, "SUBMIT", body.tx_hash)
        return await fulfillment.deliver_call(s, tx, user.id)

    return await idempotent(user.id, "deliver", idempotency_key(request), body.model_dump(mode="json"), execute)
