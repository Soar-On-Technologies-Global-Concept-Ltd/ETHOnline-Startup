"""Deterministic trust score (schematics §11.2): explainable, and the AI can describe it but never change it."""
from dataclasses import asdict, dataclass

from app.integrations.graph import ProviderStats


@dataclass(frozen=True)
class SeededHistory:
    completed: int = 0
    disputes: int = 0
    funded: int = 0


@dataclass(frozen=True)
class TrustCard:
    score: int
    label: str
    completed_jobs: int
    dispute_rate: float
    refund_share: float
    median_hours_to_evidence: float | None
    observed_jobs: int
    seeded_jobs: int
    source: str
    stale: bool

    def as_json(self) -> dict:
        return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def compute(stats: ProviderStats | None, seeded: SeededHistory, *, available: bool) -> TrustCard:
    funded = (stats.funded if stats else 0)
    completed = (stats.released + stats.settled) if stats else 0
    disputes = stats.disputes if stats else 0
    refund_share = (stats.refunded_micro / max(stats.paid_out_micro + stats.refunded_micro, 1)) if stats else 0.0
    hours = (stats.seconds_to_evidence_total / max(stats.evidence_anchored, 1) / 3600) if stats and stats.evidence_anchored else None
    all_funded = funded + seeded.funded
    all_completed = completed + seeded.completed
    all_disputes = disputes + seeded.disputes
    if not available:
        return TrustCard(50, "trust data unavailable", all_completed, 0.0, 0.0, None, funded, seeded.funded, "unavailable", True)
    if all_funded < 3:
        return TrustCard(50, "new provider", all_completed, all_disputes / max(all_funded, 1), refund_share, hours, funded, seeded.funded,
                         "the_graph", False)
    completion_rate = all_completed / all_funded
    dispute_rate = all_disputes / all_funded
    speed = _clamp(1 - (hours or 24) / 72)
    score = round(100 * (0.4 * completion_rate + 0.3 * (1 - dispute_rate) + 0.2 * (1 - refund_share) + 0.1 * speed))
    label = "trusted" if score >= 75 else ("ok" if score >= 40 else "low trust")
    return TrustCard(int(_clamp(score, 0, 100)), label, all_completed, dispute_rate, refund_share, hours, funded, seeded.funded, "the_graph", False)
