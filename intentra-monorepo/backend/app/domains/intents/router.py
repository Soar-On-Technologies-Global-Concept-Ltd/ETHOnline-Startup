"""POST /v1/intents — a sentence becomes a structured job and an open transaction (FR-2); GET reads one back."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.db import sessionmaker

from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.core.logging import transaction_id_var
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.intents import ai as intent_parser
from app.domains.intents import service as intents
from app.domains.intents.schemas import IntentIn

router = APIRouter(tags=["intents"])


@router.post("/intents", summary="Describe a job")
async def create(body: IntentIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def prepare():
        """The model runs before the database transaction opens: it can take seconds."""
        return await intent_parser.parse(body.text)

    async def execute(s, parsed):
        if body.intent_id is not None:
            intent = await intents.owned_by(s, body.intent_id, user.id)
            intent, tx = await intents.refine(s, intent, user.id, body.text, parsed)
        else:
            intent, tx = await intents.capture(s, user.id, body.text, parsed)
        transaction_id_var.set(str(tx.id))
        return 201, {"intent_id": str(intent.id), "transaction_id": str(tx.id), "status": intent.status,
                     "spec": intent.structured, "clarifying_question": intent.clarifying_question, "state": tx.state}

    return await idempotent(user.id, "intents", idempotency_key(request, required=False), body.model_dump(mode="json"),
                            execute, prepare)


@router.get("/intents/{intent_id}", summary="Read a request back")
async def read(intent_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        return await intents.view(s, intent_id, user.id)
