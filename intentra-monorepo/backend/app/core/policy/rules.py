"""Deterministic rules, in the order evaluate() runs them (schematics §6). Each returns (decision, reason) or None."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.core.money import within_tolerance
from app.core.states import TxState


class Decision(StrEnum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class AuthorizationView:
    max_amount_minor: int
    provider_address: str
    scope_hash: str
    expires_at: datetime


@dataclass(frozen=True)
class Action:
    kind: str                       # quote_select | authorize | fund | release | settle | complaint
    state: str
    currency: str
    amount_minor: int | None = None
    provider_verified: bool = True
    provider_address: str | None = None
    scope_hash: str | None = None
    human_check_ok: bool | None = None


@dataclass(frozen=True)
class PolicyContext:
    transaction_currency: str
    hard_cap_minor: int
    tolerance_bps: int
    now: datetime
    authorization: AuthorizationView | None = None


ALLOWED_STATES: dict[str, set[TxState]] = {
    "quote_select": {TxState.INTENT_STRUCTURED},
    "authorize": {TxState.AWAITING_AUTHORIZATION},
    "fund": {TxState.AUTHORIZED, TxState.FUNDING},
    "release": {TxState.DELIVERED},
    "settle": {TxState.PROPOSED},
    "complaint": {TxState.DELIVERED},
}
NEEDS_AUTHORIZATION = {"fund", "release", "settle"}
AMOUNT_CHECKED = {"authorize", "fund", "settle"}


def state_not_permitted(a: Action, c: PolicyContext):
    allowed = ALLOWED_STATES.get(a.kind)
    if allowed is not None and TxState(a.state) not in allowed:
        return Decision.BLOCK, "state_not_permitted"


def currency_conversion(a: Action, c: PolicyContext):
    if a.currency != c.transaction_currency:
        return Decision.BLOCK, "currency_conversion"


def over_hard_cap(a: Action, c: PolicyContext):
    if a.kind in ("authorize", "fund") and a.amount_minor is not None and a.amount_minor > c.hard_cap_minor:
        return Decision.BLOCK, "over_hard_cap"


def unverified_provider(a: Action, c: PolicyContext):
    if a.kind in ("quote_select", "authorize", "fund") and not a.provider_verified:
        return Decision.BLOCK, "unverified_provider"


def human_check_missing(a: Action, c: PolicyContext):
    if a.kind in ("authorize", "complaint") and a.human_check_ok is not True:
        return Decision.BLOCK, "human_check_missing"


def no_authorization(a: Action, c: PolicyContext):
    if a.kind in NEEDS_AUTHORIZATION and c.authorization is None:
        return Decision.ASK, "no_authorization"


def authorization_expired(a: Action, c: PolicyContext):
    if a.kind == "fund" and c.authorization is not None and c.authorization.expires_at <= c.now:
        return Decision.BLOCK, "authorization_expired"


def over_authorized(a: Action, c: PolicyContext):
    if a.kind not in AMOUNT_CHECKED or c.authorization is None or a.amount_minor is None:
        return None
    cap = c.authorization.max_amount_minor
    if a.amount_minor <= cap:
        return None
    if within_tolerance(a.amount_minor, cap, c.tolerance_bps):
        return Decision.ASK, "over_authorized_within_tolerance"
    return Decision.BLOCK, "over_authorized_beyond_tolerance"


def provider_substituted(a: Action, c: PolicyContext):
    if a.kind == "fund" and c.authorization is not None and a.provider_address \
            and a.provider_address.lower() != c.authorization.provider_address.lower():
        return Decision.ASK, "provider_substituted"


def scope_changed(a: Action, c: PolicyContext):
    if a.kind == "fund" and c.authorization is not None and a.scope_hash and a.scope_hash != c.authorization.scope_hash:
        return Decision.ASK, "scope_changed"


RULES = [state_not_permitted, currency_conversion, over_hard_cap, unverified_provider, human_check_missing,
         no_authorization, authorization_expired, over_authorized, provider_substituted, scope_changed]
