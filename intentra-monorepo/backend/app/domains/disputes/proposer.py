"""FR-17 (L2): propose one remedy with cited evidence. The dispute ladder validates the result; the split comes from REMEDY_BPS."""
import uuid
from dataclasses import dataclass

from app.core.remedies import Remedy
from app.integrations.llm.client import llm
from app.integrations.llm.schemas import RemedyProposal


@dataclass(frozen=True)
class Proposal:
    remedy: Remedy
    cited_evidence_ids: list[uuid.UUID]
    rationale: str
    confidence: float
    model: str
    prompt_version: str
    input_hash: str


async def propose(scope: dict, catalog: list[dict], complaint: dict, response: str | None, coverage: dict) -> Proposal:
    """Raises AIUnavailable on timeout, refusal or invalid output; the ladder escalates."""
    result = await llm().run("resolve", {"scope": scope, "evidence_catalog": catalog, "complaint": complaint,
                                         "response": response, "coverage": coverage}, RemedyProposal, max_tokens=4096)
    o = result.output
    return Proposal(o.remedy, list(o.cited_evidence_ids), o.rationale, o.confidence, result.model, result.prompt_version, result.input_hash)
