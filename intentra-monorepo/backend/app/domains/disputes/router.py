"""Respond, read the proposal, accept or reject (FR-16 to FR-18)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.db import sessionmaker
from app.core.errors import Conflict, NotFound
from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.domains.disputes import service as disputes
from app.domains.disputes.schemas import AcceptIn, RejectIn, RespondIn
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock

router = APIRouter(tags=["disputes"])


async def _load(s, dispute_id: uuid.UUID, user: CurrentUser):
    dispute = await disputes.by_id(s, dispute_id)
    tx, role = await load_transaction(s, dispute.transaction_id, user)
    return dispute, tx, role


@router.post("/disputes/{dispute_id}/respond", summary="The provider's side of the story")
async def respond(dispute_id: uuid.UUID, body: RespondIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        dispute, tx, role = await _load(s, dispute_id, user)
        require("provider", role)
        tx = await lock(s, tx.id)
        return await disputes.respond(s, tx, dispute, user.id, body.text)

    response = await idempotent(user.id, "respond", idempotency_key(request, required=False),
                                body.model_dump(mode="json"), execute)
    if response.status_code == 200:
        disputes.schedule_ladder(dispute_id)      # the ladder runs after the response is committed
    return response


@router.get("/disputes/{dispute_id}/proposal", summary="The proposed resolution and the data to sign")
async def proposal(dispute_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        dispute, tx, _ = await _load(s, dispute_id, user)
        return await disputes.proposal_view(s, tx, dispute)


@router.post("/disputes/{dispute_id}/accept", summary="Sign the proposed resolution")
async def accept(dispute_id: uuid.UUID, body: AcceptIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        dispute, tx, role = await _load(s, dispute_id, user)
        if role not in ("customer", "provider"):
            raise Conflict("only the two parties can sign a resolution", code="wrong_role")
        tx = await lock(s, tx.id)
        proposal_row = await disputes.proposal_for(s, dispute.id)
        if proposal_row is None:
            raise NotFound("there is no proposal to sign yet")
        return await disputes.accept(s, tx, dispute, proposal_row, user.id, role, body.signature)

    return await idempotent(user.id, "accept", idempotency_key(request), body.model_dump(mode="json"), execute)


@router.post("/disputes/{dispute_id}/reject", summary="Reject the proposal and send it to a person")
async def reject(dispute_id: uuid.UUID, body: RejectIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        dispute, tx, role = await _load(s, dispute_id, user)
        if role not in ("customer", "provider"):
            raise Conflict("only the two parties can reject a resolution", code="wrong_role")
        tx = await lock(s, tx.id)
        proposal_row = await disputes.proposal_for(s, dispute.id)
        if proposal_row is None:
            raise NotFound("there is no proposal to reject yet")
        return await disputes.reject(s, tx, dispute, proposal_row, user.id, role, body.reason)

    return await idempotent(user.id, "reject", idempotency_key(request), body.model_dump(mode="json"), execute)
