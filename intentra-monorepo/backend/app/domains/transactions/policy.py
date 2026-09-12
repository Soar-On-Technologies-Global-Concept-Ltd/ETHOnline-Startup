"""Policy at the transaction boundary: build the context, enforce the decision, and record every refusal in the trail.

The rules themselves are pure functions in core/policy. This module is where a refusal becomes an audited event and an
HTTP error, and it is what other domains call before any high-impact step.
"""
import logging

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.db import session_scope
from app.core.logging import log
from app.core.money import kobo_to_micro_usdc, naira_to_kobo
from app.core.policy import engine as policy
from app.core.states import TxState
from app.domains.audit import service as audit
from app.integrations.arc import eip712

logger = logging.getLogger("policy")

Action = policy.Action
AuthorizationView = policy.AuthorizationView
Decision = policy.Decision


def context(tx, authorization: AuthorizationView | None = None) -> policy.PolicyContext:
    """Callers pass the authorization they already loaded, so policy never has to reach into another domain."""
    settings = get_settings()
    rate = tx.fx_rate_ngn_per_usdc or settings.demo_fx_rate_ngn_per_usdc
    return policy.PolicyContext(transaction_currency=tx.currency,
                                hard_cap_minor=kobo_to_micro_usdc(naira_to_kobo(settings.policy_hard_cap_ngn), rate),
                                tolerance_bps=settings.ask_tolerance_bps, now=utcnow(), authorization=authorization)


async def note_out_of_band(transaction_id, state: str, actor: str, event: str, payload: dict) -> None:
    """A refusal rolls back its own request, so the note is written on its own connection."""
    try:
        async with session_scope() as s:
            await audit.append(s, transaction_id=transaction_id, actor=actor, event=event,
                               from_state=state, to_state=state, payload=payload)
    except Exception as err:
        log(logger, "could not record the policy note", error=f"{type(err).__name__}: {err}")


async def enforce(tx, actor: str, action: Action, ctx: policy.PolicyContext, details: dict | None = None) -> None:
    """ALLOW continues. BLOCK and ASK are recorded in the trail and then raised as 403 or 409."""
    result = policy.evaluate(action, ctx)
    if result.decision is Decision.ALLOW:
        return
    note = "POLICY_BLOCKED" if result.decision is Decision.BLOCK else "POLICY_ASK"
    await note_out_of_band(tx.id, tx.state, actor, note, {"action": action.kind, "reason": result.reason, "state": tx.state})
    extra = dict(details or {})
    if result.decision is Decision.ASK and tx.state == TxState.AWAITING_AUTHORIZATION.value and tx.authorization_offer:
        extra["authorization_typed_data"] = eip712.for_client(tx.authorization_offer["typed_data"])
    policy.enforce(result, extra)
