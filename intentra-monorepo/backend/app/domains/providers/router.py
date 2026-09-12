"""Ranked providers for a request, and one provider's trust card (FR-3, FR-19).

Ranking is deterministic and happens in code; the model only writes the why and trade-off lines.
"""
import uuid

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.db import session_scope, sessionmaker
from app.core.errors import Conflict, NotFound
from app.core.money import kobo_to_micro_usdc
from app.domains.identity.deps import CurrentUser, current_user
from app.domains.intents import service as intents
from app.domains.providers import ai as recommender
from app.domains.providers import ranking
from app.domains.providers import service as providers
from app.domains.providers import trust as trust_service
from app.domains.providers.schemas import ProviderOnboardRequest

router = APIRouter(tags=["providers"])


@router.get("/providers/recommendations", summary="Ranked providers for a request")
async def recommendations(intent_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    settings = get_settings()
    async with sessionmaker()() as s:
        intent = await intents.owned_by(s, intent_id, user.id)
        if not intent.structured:
            raise Conflict("this request still needs a detail", code="intent_incomplete",
                           details={"clarifying_question": intent.clarifying_question})
        spec = dict(intent.structured)
        rows = await providers.list_all(s)
        cards = await trust_service.cards(s, rows)
        wallets = await providers.wallets_for(s, rows)
    kept, dropped = ranking.rank(rows, spec, cards, wallets, settings.trust_min)

    async with session_scope() as s:
        intent = await intents.get(s, intent_id)
        priced = []
        for rank, candidate in enumerate(kept, start=1):
            quote = await intents.upsert_quote(s, intent, candidate.provider_id, candidate.display_name, spec,
                                               candidate.price_minor, candidate.trust.as_json(), rank)
            priced.append({"rank": rank, "candidate": candidate, "quote_id": str(quote.id), "scope": quote.scope,
                           "scope_hash": quote.scope_hash, "expires_at": quote.expires_at})

    request_summary = {"area": spec["area"], "rooms": spec["rooms"], "date": spec["date"],
                       "budget_max_minor": spec["budget_max_minor"], "currency": "NGN"}
    texts = await recommender.explain(request_summary, [
        {"quote_id": row["quote_id"], "provider": row["candidate"].display_name, "price_minor": row["candidate"].price_minor,
         "trust": {**row["candidate"].trust.as_json(), "seeded_jobs": row["candidate"].trust.seeded_jobs}} for row in priced])

    async with session_scope() as s:
        for row in priced:
            text = texts.get(row["quote_id"], {})
            await intents.describe_quote_text(s, uuid.UUID(row["quote_id"]), text.get("why"), text.get("trade_offs"))

    rate = settings.demo_fx_rate_ngn_per_usdc
    return {"intent_id": str(intent_id), "request": request_summary,
            "items": [{"rank": row["rank"], "quote_id": row["quote_id"],
                       "provider": {"id": str(row["candidate"].provider_id), "display_name": row["candidate"].display_name,
                                    "seeded": row["candidate"].seeded, "ready": row["candidate"].ready},
                       "price": {"amount_minor": row["candidate"].price_minor, "currency": "NGN",
                                 "settlement_minor": kobo_to_micro_usdc(row["candidate"].price_minor, rate),
                                 "settlement_currency": "USDC", "fx_rate": rate, "label": "demo rate"},
                       "trust": row["candidate"].trust.as_json(),
                       "why": texts.get(row["quote_id"], {}).get("why"),
                       "trade_offs": texts.get(row["quote_id"], {}).get("trade_offs"),
                       "scope": row["scope"], "scope_hash": row["scope_hash"], "expires_at": row["expires_at"]}
                      for row in priced],
            "excluded": [{"provider_id": str(e.provider_id), "reason": e.reason} for e in dropped]}


@router.get("/providers/{provider_id}/trust", summary="A provider's trust card")
async def trust(provider_id: uuid.UUID, user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        summary = await providers.summary(s, provider_id)
        if summary is None:
            raise NotFound("provider not found")
        card = await trust_service.card_for(s, await providers.get(s, provider_id))
    return {"provider": summary, "trust": card.as_json()}


@router.post("/providers/onboard", summary="Onboard as a new provider")
async def onboard(req: ProviderOnboardRequest, user: CurrentUser = Depends(current_user)) -> dict:
    async with session_scope() as s:
        provider = await providers.onboard_user(s, user.id, req.trade, req.areas, req.base_rate_minor)
        return {
            "id": str(provider.id),
            "trade": provider.trade,
            "areas": provider.areas,
            "base_rate_minor": provider.base_rate_minor
        }


@router.get("/providers/me", summary="Get the current user's provider profile")
async def get_my_profile(user: CurrentUser = Depends(current_user)) -> dict:
    async with sessionmaker()() as s:
        provider = await providers.for_user(s, user.id)
        if not provider:
            raise NotFound("not a provider", code="not_provider")
        return {
            "id": str(provider.id),
            "display_name": provider.display_name,
            "trade": provider.trade,
            "areas": provider.areas,
            "base_rate_minor": provider.base_rate_minor,
            "verified": provider.verified
        }
