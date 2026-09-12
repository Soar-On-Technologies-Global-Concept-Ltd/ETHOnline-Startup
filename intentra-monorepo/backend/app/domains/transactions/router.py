"""Choose a provider, then read the transaction: the two screens the customer spends the most time on (FR-4, FR-20)."""
import uuid

from fastapi import APIRouter, Depends, Request

from app.core.db import sessionmaker
from app.core.errors import Conflict, NotFound
from app.core.http import idempotency_key
from app.core.idempotency import run as idempotent
from app.domains.identity import service as identity
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.intents import service as intents
from app.domains.payments import service as payments
from app.domains.providers import service as providers
from app.domains.transactions import service as transactions
from app.domains.transactions import views
from app.domains.transactions.deps import load_transaction, require
from app.domains.transactions.machine import lock
from app.domains.transactions.schemas import CancelIn, SelectQuoteIn

router = APIRouter(tags=["transactions"])


def _no_wallet(who: str) -> None:
    raise Conflict(f"{who} does not have an Intentra wallet yet", code="wallet_not_ready")


@router.post("/transactions", summary="Choose a provider and get the approval to sign")
async def create(body: SelectQuoteIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        quote = await intents.quote_view(s, body.quote_id)
        if quote is None or quote["intent_id"] != str(body.intent_id):
            raise NotFound("quote not found")
        tx = await transactions.by_intent_locked(s, body.intent_id)
        if tx.customer_id != user.id:
            raise NotFound("request not found")
        provider = await providers.summary(s, quote["provider_id"])
        if provider is None:
            raise NotFound("provider not found")
        customer_wallet = await identity.wallet_of(s, user.id)
        provider_wallet = await providers.wallet_of(s, quote["provider_id"])
        if customer_wallet is None:
            _no_wallet("your account")
        if provider_wallet is None:
            _no_wallet(provider["display_name"])
        return await transactions.select_quote(s, tx, user.id, quote, provider, customer_wallet, provider_wallet)

    return await idempotent(user.id, "transactions", idempotency_key(request, required=False),
                            body.model_dump(mode="json"), execute)


@router.get("/transactions/{tx_id}", summary="Everything the screen needs")
async def get_one(tx_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        tx, role = await load_transaction(s, tx_id, user)
        return await views.transaction(s, tx, role)


@router.get("/transactions/{tx_id}/timeline", summary="The audit trail, with its hash chain verified")
async def timeline(tx_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        tx, _ = await load_transaction(s, tx_id, user)
        return await views.timeline(s, tx)


@router.post("/transactions/{tx_id}/cancel", summary="Cancel before any money moves")
async def cancel(tx_id: uuid.UUID, body: CancelIn, request: Request, user: CurrentUser = Depends(current_user)):
    async def execute(s, _):
        tx = await lock(s, tx_id)
        _, role = await load_transaction(s, tx_id, user)
        require("customer", role)
        return await transactions.cancel(s, tx, user.id, body.reason, await payments.has_pending_funding(s, tx.id))

    return await idempotent(user.id, "cancel", idempotency_key(request, required=False), body.model_dump(mode="json"), execute)
