"""The resolution ladder (schematics §14): deterministic L1 rules first, then L2 with the model — validated before it counts."""
import logging
import uuid
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.remedies import REMEDY_BPS, Remedy
from app.core.logging import log
from app.domains.disputes import coverage as evidence_analyzer, proposer as resolution_proposer
from app.integrations.llm.client import AIUnavailable
from app.core.explanation import RATIONALES

logger = logging.getLogger("ladder")


@dataclass(frozen=True)
class LadderInput:
    amount_minor: int
    scope: dict
    checklist: list[str]
    catalog: list[dict]
    complaint: dict            # {category, text}
    response: str | None
    evidence_ids: set[str]


@dataclass(frozen=True)
class LadderResult:
    level: str
    remedy: Remedy | None = None
    provider_bps: int | None = None
    rationale: str = ""
    cited_evidence_ids: list[uuid.UUID] = field(default_factory=list)
    confidence: float | None = None
    model: str | None = None
    prompt_version: str | None = None
    input_hash: str | None = None
    coverage: dict = field(default_factory=dict)
    escalate_reason: str | None = None

    @property
    def escalated(self) -> bool:
        return self.remedy is None


def _provider_photos(catalog: list[dict]) -> list[dict]:
    return [e for e in catalog if e["kind"] == "AFTER_PHOTO" and e["by"] == "provider"]


def l1(data: LadderInput, coverage: dict) -> LadderResult | None:
    """Rules that decide without a model. Everything else goes to L2."""
    if data.complaint["category"] == "NO_SHOW" and not _provider_photos(data.catalog):
        cited = [uuid.UUID(e["id"]) for e in data.catalog if e["by"] == "customer"]
        if cited:
            return LadderResult("L1", Remedy.REFUND_FULL, REMEDY_BPS[Remedy.REFUND_FULL], RATIONALES["REFUND_FULL"],
                                cited, 1.0, coverage=coverage)
    return None


async def decide(data: LadderInput) -> LadderResult:
    s = get_settings()
    coverage = await evidence_analyzer.coverage_notes(data.checklist, data.catalog)
    decided = l1(data, coverage)
    if decided is not None:
        log(logger, "L1 decided", remedy=decided.remedy)
        return decided
    if data.amount_minor > s.l2_max_amount_minor:
        return LadderResult("L2", coverage=coverage, escalate_reason="over the amount a proposal may cover")
    try:
        proposal = await resolution_proposer.propose(data.scope, data.catalog, data.complaint, data.response, coverage)
    except AIUnavailable as err:
        return LadderResult("L2", coverage=coverage, escalate_reason=f"the assistant could not produce a proposal ({err})")
    foreign = [str(i) for i in proposal.cited_evidence_ids if str(i) not in data.evidence_ids]
    if foreign:
        log(logger, "L2 cited foreign evidence", count=len(foreign))
        return LadderResult("L2", coverage=coverage, escalate_reason="the proposal cited evidence from outside this transaction")
    if proposal.confidence < s.l2_min_confidence:
        return LadderResult("L2", coverage=coverage, escalate_reason="the assistant was not confident enough")
    remedy = Remedy(proposal.remedy)
    return LadderResult("L2", remedy, REMEDY_BPS[remedy], proposal.rationale, list(proposal.cited_evidence_ids),
                        proposal.confidence, proposal.model, proposal.prompt_version, proposal.input_hash, coverage)
