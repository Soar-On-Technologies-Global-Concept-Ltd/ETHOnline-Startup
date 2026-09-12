"""Deterministic ranking (schematics §8.2). The model never reorders this list; it only writes the why and trade-off lines."""
import datetime as dt
import uuid
from dataclasses import dataclass

from app.domains.providers.score import TrustCard


@dataclass(frozen=True)
class Candidate:
    provider_id: uuid.UUID
    display_name: str
    seeded: bool
    price_minor: int
    trust: TrustCard
    ready: bool          # the provider has an Intentra wallet, so they can be paid


@dataclass(frozen=True)
class Excluded:
    provider_id: uuid.UUID
    reason: str


def price_for(base_rate_minor: int, rooms: int) -> int:
    return int(base_rate_minor) * int(rooms)


def _serves(areas: list[str], area: str) -> bool:
    return not areas or area.strip().lower() in {a.strip().lower() for a in areas}


def _free_on(available: list[dt.date], day: dt.date) -> bool:
    return not available or day in available


def rank(providers: list, spec: dict, cards: dict[uuid.UUID, TrustCard], wallets: dict[uuid.UUID, str],
         trust_min: int) -> tuple[list[Candidate], list[Excluded]]:
    day = dt.date.fromisoformat(spec["date"])
    kept: list[Candidate] = []
    dropped: list[Excluded] = []
    for p in providers:
        card = cards.get(p.id)
        price = price_for(p.base_rate_minor, spec["rooms"])
        reason = None
        if p.trade != spec["service"]:
            reason = "different trade"
        elif not p.verified:
            reason = "not verified"
        elif not _serves(list(p.areas or []), spec["area"]):
            reason = "does not serve this area"
        elif not _free_on(list(p.available_dates or []), day):
            reason = "not available that day"
        elif price > int(spec["budget_max_minor"]):
            reason = "over budget"
        elif card is not None and card.score < trust_min:
            reason = "trust below the minimum"
        if reason:
            dropped.append(Excluded(p.id, reason))
            continue
        kept.append(Candidate(p.id, p.display_name, p.seeded, price, card, p.id in wallets))
    kept.sort(key=lambda c: (-c.trust.score, c.price_minor, str(c.provider_id)))
    return kept, dropped
