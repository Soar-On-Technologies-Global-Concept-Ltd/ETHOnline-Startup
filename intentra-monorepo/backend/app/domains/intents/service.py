"""What the customer asked for, and the priced offers that answer it.

The model structures the sentence; this domain decides nothing about money beyond arithmetic the code owns.
"""
import re
import uuid
from datetime import timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.errors import Conflict, NotFound
from app.core.hashing import scope_hash
from app.core.states import Event, TxState
from app.domains.intents.models import Intent, Quote
from app.domains.transactions import machine
from app.domains.transactions import service as transactions


async def get(s: AsyncSession, intent_id: uuid.UUID) -> Intent:
    intent = await s.get(Intent, intent_id)
    if intent is None:
        raise NotFound("request not found")
    return intent


async def owned_by(s: AsyncSession, intent_id: uuid.UUID, customer_id: uuid.UUID) -> Intent:
    """Someone else's request is not visible, so it reads as missing rather than forbidden."""
    intent = await s.get(Intent, intent_id)
    if intent is None or intent.customer_id != customer_id:
        raise NotFound("request not found")
    return intent


async def get_quote(s: AsyncSession, quote_id: uuid.UUID | None) -> Quote | None:
    return None if quote_id is None else await s.get(Quote, quote_id)


async def quote_view(s: AsyncSession, quote_id: uuid.UUID | None) -> dict | None:
    """What other domains need from a quote: never the row itself."""
    quote = await get_quote(s, quote_id)
    if quote is None:
        return None
    return {"id": str(quote.id), "intent_id": str(quote.intent_id), "provider_id": quote.provider_id,
            "amount_minor": quote.amount_minor, "currency": quote.currency, "scope": quote.scope,
            "scope_hash": quote.scope_hash, "expires_at": quote.expires_at}


def build_scope(spec: dict, provider_name: str, price_minor: int) -> dict:
    """The agreed scope. It is hashed into the signed authorization, so it holds integers and strings only."""
    rooms = int(spec["rooms"])
    coats = 2
    for requirement in spec.get("requirements", []):
        if m := re.search(r"(\d+)\s*coats?", str(requirement), re.I):
            coats = int(m.group(1))
    return {"service": spec["service"], "area": spec["area"], "rooms": rooms, "coats": coats, "paint_included": True,
            "date": spec["date"], "checklist": [f"bedroom_{i}" for i in range(1, rooms + 1)], "after_photos_per_room": 1,
            "provider": provider_name, "amount_minor": int(price_minor), "currency": "NGN",
            "requirements": [str(r) for r in spec.get("requirements", [])]}


async def upsert_quote(s: AsyncSession, intent: Intent, provider_id: uuid.UUID, provider_name: str, spec: dict,
                       price_minor: int, trust_snapshot: dict, rank: int) -> Quote:
    """One quote per (intent, provider): reloading the recommendations never creates duplicates."""
    scope = build_scope(spec, provider_name, price_minor)
    expires_at = utcnow() + timedelta(seconds=get_settings().quote_ttl_seconds)
    row = (await s.exec(select(Quote).where(Quote.intent_id == intent.id, Quote.provider_id == provider_id)
                        .order_by(Quote.version.desc()).limit(1))).first()
    if row is None:
        row = Quote(intent_id=intent.id, provider_id=provider_id, amount_minor=price_minor, currency="NGN", scope=scope,
                    scope_hash=scope_hash(scope), version=1, rank=rank, trust_snapshot=trust_snapshot, expires_at=expires_at)
    else:
        row.amount_minor, row.scope, row.scope_hash = price_minor, scope, scope_hash(scope)
        row.rank, row.trust_snapshot, row.expires_at = rank, trust_snapshot, expires_at
    s.add(row)
    await s.flush()
    return row


async def describe_quote_text(s: AsyncSession, quote_id: uuid.UUID, why: str | None, trade_offs: str | None) -> None:
    quote = await s.get(Quote, quote_id)
    if quote is not None:
        quote.why, quote.trade_offs = why, trade_offs
        s.add(quote)


async def capture(s: AsyncSession, customer_id: uuid.UUID, text: str, parsed) -> tuple[Intent, object]:
    """A sentence becomes a stored request and an open transaction, whether or not the model could structure it."""
    intent = Intent(customer_id=customer_id, raw_text=text, structured=parsed.spec,
                    clarifying_question=parsed.clarifying_question,
                    status="STRUCTURED" if parsed.spec else "NEEDS_CLARIFICATION", ai_model=parsed.model,
                    prompt_version=parsed.prompt_version)
    s.add(intent)
    await s.flush()
    tx = await transactions.open_for_intent(s, customer_id, intent.id, parsed.spec, parsed.model)
    return intent, tx


async def refine(s: AsyncSession, intent: Intent, customer_id: uuid.UUID, text: str, parsed) -> tuple[Intent, object]:
    """The customer answers a clarifying question: the same request, now complete."""
    tx = await transactions.by_intent_locked(s, intent.id)
    if tx.state not in (TxState.CREATED.value, TxState.INTENT_STRUCTURED.value):
        raise Conflict("this job has already moved on; start a new request", details={"state": tx.state})
    intent.raw_text = f"{intent.raw_text}\n{text}"
    intent.structured, intent.clarifying_question = parsed.spec, parsed.clarifying_question
    intent.status = "STRUCTURED" if parsed.spec else "NEEDS_CLARIFICATION"
    intent.ai_model, intent.prompt_version = parsed.model, parsed.prompt_version
    s.add(intent)
    if parsed.spec and tx.state == TxState.CREATED.value:
        await machine.apply(s, tx, Event.INTENT_STRUCTURED, f"customer:{customer_id}",
                            {"intent_id": str(intent.id), "spec": parsed.spec})
    else:
        await machine.note(s, tx, f"customer:{customer_id}", "INTENT_REFINED", {"intent_id": str(intent.id)})
    return intent, tx
