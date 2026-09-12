"""One test per rule, plus the Blueprint's ₦165k / ₦198k / ₦220k band (schematics §6)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.money import kobo_to_micro_usdc, naira_to_kobo
from app.core.states import TxState
from app.core.policy.engine import Decision, evaluate
from app.core.policy.rules import Action, AuthorizationView, PolicyContext

RATE = 1650
NOW = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
CAP = kobo_to_micro_usdc(naira_to_kobo(250_000), RATE)
AUTHORIZED = kobo_to_micro_usdc(naira_to_kobo(180_000), RATE)


def naira(amount: int) -> int:
    return kobo_to_micro_usdc(naira_to_kobo(amount), RATE)


def context(authorization: AuthorizationView | None = None, now: datetime = NOW) -> PolicyContext:
    return PolicyContext(transaction_currency="USDC", hard_cap_minor=CAP, tolerance_bps=1000, now=now,
                         authorization=authorization)


def authorization(expires_in_minutes: int = 15, provider: str = "0x" + "11" * 20, scope: str = "0xscope") -> AuthorizationView:
    return AuthorizationView(AUTHORIZED, provider, scope, NOW + timedelta(minutes=expires_in_minutes))


def fund(amount: int, **kwargs) -> Action:
    defaults = {"kind": "fund", "state": TxState.AUTHORIZED.value, "currency": "USDC", "amount_minor": amount,
                "provider_address": "0x" + "11" * 20, "scope_hash": "0xscope"}
    return Action(**{**defaults, **kwargs})


def test_within_the_authorised_maximum_is_allowed():
    assert evaluate(fund(naira(165_000)), context(authorization())).decision is Decision.ALLOW


def test_ten_percent_over_asks_for_a_new_signature():
    result = evaluate(fund(naira(198_000)), context(authorization()))
    assert (result.decision, result.reason) == (Decision.ASK, "over_authorized_within_tolerance")


def test_far_over_is_blocked():
    result = evaluate(fund(naira(220_000)), context(authorization()))
    assert (result.decision, result.reason) == (Decision.BLOCK, "over_authorized_beyond_tolerance")


def test_over_the_hard_cap_is_blocked():
    result = evaluate(fund(naira(300_000)), context(authorization()))
    assert (result.decision, result.reason) == (Decision.BLOCK, "over_hard_cap")


def test_state_not_permitted():
    result = evaluate(fund(naira(165_000), state=TxState.DELIVERED.value), context(authorization()))
    assert (result.decision, result.reason) == (Decision.BLOCK, "state_not_permitted")


def test_currency_conversion_is_blocked():
    result = evaluate(fund(naira(165_000), currency="NGN"), context(authorization()))
    assert (result.decision, result.reason) == (Decision.BLOCK, "currency_conversion")


def test_unverified_provider_is_blocked():
    result = evaluate(fund(naira(165_000), provider_verified=False), context(authorization()))
    assert (result.decision, result.reason) == (Decision.BLOCK, "unverified_provider")


def test_a_complaint_needs_a_human_check():
    action = Action(kind="complaint", state=TxState.DELIVERED.value, currency="USDC", human_check_ok=None)
    result = evaluate(action, context())
    assert (result.decision, result.reason) == (Decision.BLOCK, "human_check_missing")


def test_authorising_needs_a_human_check():
    action = Action(kind="authorize", state=TxState.AWAITING_AUTHORIZATION.value, currency="USDC",
                    amount_minor=naira(165_000), human_check_ok=False)
    assert evaluate(action, context()).reason == "human_check_missing"


def test_funding_without_an_authorization_asks():
    result = evaluate(fund(naira(165_000)), context(None))
    assert (result.decision, result.reason) == (Decision.ASK, "no_authorization")


def test_an_expired_authorization_is_blocked():
    result = evaluate(fund(naira(165_000)), context(authorization(expires_in_minutes=-1)))
    assert (result.decision, result.reason) == (Decision.BLOCK, "authorization_expired")


def test_a_substituted_provider_asks():
    result = evaluate(fund(naira(165_000), provider_address="0x" + "99" * 20), context(authorization()))
    assert (result.decision, result.reason) == (Decision.ASK, "provider_substituted")


def test_a_changed_scope_asks():
    result = evaluate(fund(naira(165_000), scope_hash="0xdifferent"), context(authorization()))
    assert (result.decision, result.reason) == (Decision.ASK, "scope_changed")


def test_release_and_settle_run_their_own_checks():
    allowed = Action(kind="release", state=TxState.DELIVERED.value, currency="USDC", amount_minor=naira(165_000))
    assert evaluate(allowed, context(authorization())).decision is Decision.ALLOW
    settle = Action(kind="settle", state=TxState.PROPOSED.value, currency="USDC", amount_minor=naira(165_000))
    assert evaluate(settle, context(authorization())).decision is Decision.ALLOW


@pytest.mark.parametrize("kind", ["quote_select", "authorize", "fund", "release", "settle", "complaint"])
def test_every_checkpoint_refuses_the_wrong_state(kind: str):
    action = Action(kind=kind, state=TxState.CANCELLED.value, currency="USDC", amount_minor=1, human_check_ok=True)
    assert evaluate(action, context(authorization())).reason == "state_not_permitted"
