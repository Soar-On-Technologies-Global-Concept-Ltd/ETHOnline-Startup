"""The trust score is deterministic and explainable (schematics §11.2)."""
from app.integrations.graph import ProviderStats
from app.domains.providers.score import SeededHistory, compute


def stats(**kwargs) -> ProviderStats:
    base = {"address": "0x" + "11" * 20, "funded": 10, "released": 9, "settled": 1, "refunded": 0, "disputes": 1,
            "paid_out_micro": 900_000_000, "refunded_micro": 0, "seconds_to_evidence_total": 36_000, "evidence_anchored": 10}
    return ProviderStats(**{**base, **kwargs})


def test_a_provider_with_history_scores_on_what_happened():
    card = compute(stats(), SeededHistory(), available=True)
    assert card.completed_jobs == 10 and card.dispute_rate == 0.1
    assert card.median_hours_to_evidence == 1.0
    assert card.score == round(100 * (0.4 * 1.0 + 0.3 * 0.9 + 0.2 * 1.0 + 0.1 * (1 - 1 / 72)))
    assert card.label == "trusted" and card.source == "the_graph" and card.stale is False


def test_fewer_than_three_jobs_is_a_neutral_fifty():
    card = compute(stats(funded=2, released=2, settled=0, disputes=0), SeededHistory(), available=True)
    assert (card.score, card.label) == (50, "new provider")


def test_no_graph_data_says_so_instead_of_guessing():
    card = compute(None, SeededHistory(), available=False)
    assert (card.score, card.label, card.source, card.stale) == (50, "trust data unavailable", "unavailable", True)


def test_seeded_history_counts_but_is_reported_separately():
    card = compute(None, SeededHistory(completed=14, disputes=1, funded=14), available=True)
    assert card.seeded_jobs == 14 and card.observed_jobs == 0
    assert card.completed_jobs == 14 and card.score > 50


def test_refunds_pull_the_score_down():
    clean = compute(stats(), SeededHistory(), available=True).score
    refunded = compute(stats(refunded=3, refunded_micro=300_000_000), SeededHistory(), available=True).score
    assert refunded < clean


def test_disputes_pull_the_score_down():
    assert compute(stats(disputes=5), SeededHistory(), available=True).score < compute(stats(disputes=0), SeededHistory(), available=True).score


def test_the_card_is_json_safe():
    card = compute(stats(), SeededHistory(), available=True).as_json()
    assert set(card) >= {"score", "label", "completed_jobs", "dispute_rate", "refund_share", "source", "stale"}
