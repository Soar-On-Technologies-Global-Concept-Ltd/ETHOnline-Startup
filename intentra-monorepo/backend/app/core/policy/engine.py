"""ALLOW / ASK / BLOCK before every high-impact action. Never asks a model."""
from dataclasses import dataclass

from app.core.errors import AppError
from app.core.policy.rules import RULES, Action, AuthorizationView, Decision, PolicyContext  # noqa: F401


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str | None = None

    def as_json(self) -> dict:
        return {"decision": self.decision.value, "reasons": [self.reason] if self.reason else []}


class PolicyBlocked(AppError):
    status, code = 403, "policy_block"


class PolicyAsk(AppError):
    status, code = 409, "policy_ask"


def evaluate(action: Action, ctx: PolicyContext) -> PolicyResult:
    for rule in RULES:
        hit = rule(action, ctx)
        if hit:
            return PolicyResult(hit[0], hit[1])
    return PolicyResult(Decision.ALLOW, None)


def enforce(result: PolicyResult, details: dict | None = None) -> None:
    if result.decision is Decision.BLOCK:
        raise PolicyBlocked(f"blocked by policy: {result.reason}", details={"reason": result.reason, **(details or {})})
    if result.decision is Decision.ASK:
        raise PolicyAsk(f"needs a fresh approval: {result.reason}", details={"reason": result.reason, **(details or {})})
