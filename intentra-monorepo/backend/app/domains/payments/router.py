"""Funding and release. The API returns call data; the customer's wallet sends it (FR-8, FR-13)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.core.schemas import ChainReportIn
from app.domains.identity import service as identity
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.payments import service as payments
from app.domains.payments.schemas import ReleaseIn
from app.domains.providers import service as providers
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock

router = APIRouter(tags=["payments"])


@router.post("/transactions/{tx_id}/fund", summary="Get the approve and fund calls, or report the transaction hash")
async def fund(tx_id: uuid.UUID, body: ChainReportIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        require("customer", role)
        if body.tx_hash:
            return await payments.report_chain_tx(s, tx, user.id, "FUND", body.tx_hash)
        return await payments.fund_calls(s, tx, user.id, await providers.wallet_of(s, tx.provider_id))

    return await idempotent(user.id, "fund", idempotency_key(request), body.model_dump(mode="json"), execute)


@router.post("/transactions/{tx_id}/release", summary="Release the payment to the provider")
async def release(tx_id: uuid.UUID, body: ReleaseIn, request: Request, user: CurrentUser = Depends(current_user)):
    """Empty body returns the resolution to sign; the signed body queues it for the chain."""
    async def execute(s, _):
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        require("customer", role)
        if body.tx_hash:
            return await payments.report_chain_tx(s, tx, user.id, "RELEASE", body.tx_hash)
        if body.signature:
            return await payments.release_execute(s, tx, user.id, body.signature,
                                                  await identity.wallet_of(s, user.id))
        return await payments.release_request(s, tx, user.id)

    return await idempotent(user.id, "release", idempotency_key(request), body.model_dump(mode="json"), execute)
