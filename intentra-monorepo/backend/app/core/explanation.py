"""Plain-language explanations. Templates first, so every screen has words even when the model is unavailable.

The per-state status wording lives in app/core/status_copy.py.
"""
from app.core.status_copy import CANCELLED_REFUNDED, STATUS


def status_line(state: str, role: str, close_reason: str | None = None) -> str:
    """The one sentence this role sees for this state.

    An unknown state renders as "" on purpose: a state added to the machine before its copy is written should
    leave a screen blank, not break it.
    """
    if state == "CANCELLED" and close_reason == "refunded":
        return CANCELLED_REFUNDED
    customer, provider = STATUS.get(state, ("", ""))
    return provider if role == "provider" else customer


def naira(minor: int) -> str:
    """Kobo to a display string. Money is integer minor units everywhere; this is the only place it becomes text."""
    return f"₦{minor // 100:,}"


def rec_text(quote: dict, request: dict) -> dict:
    """Template reason for recommending a provider, used when the model is unavailable or declines.

    Each branch says only what the trust data actually supports, so a missing subgraph reads as "unavailable"
    rather than as a low score. Both fields are capped at 160 characters to match the model-written version.
    """
    trust = quote["trust"]
    price = naira(quote["price_minor"])
    if trust["source"] == "unavailable":
        why = f"Serves {request['area']} and fits your budget at {price}."
        trade = "Trust data is unavailable right now, so this ranking uses a neutral score."
    elif trust["label"] == "new provider":
        why = f"Serves {request['area']} at {price}, within your budget."
        trade = "New provider: fewer than 3 jobs on-chain, so the score is a neutral 50."
    else:
        why = f"Trust {trust['score']}/100 from {trust['completed_jobs']} completed jobs; {price} is within your budget."
        trade = f"Dispute rate {round(100 * float(trust['dispute_rate']))}%." + (" Includes seeded history." if trust.get("seeded_jobs") else "")
    return {"why": why[:160], "trade_offs": trade[:160]}


# Fixed wording for each remedy. The dispute ladder picks a remedy; it never writes the sentence that explains it.
RATIONALES = {
    "RELEASE_FULL": "The provider's photos cover every item in the agreed scope and the complaint does not show missing work, so the full payment goes to the provider.",
    "SPLIT_70_30": "The after-photos show most of the agreed work was done, and the complaint credibly shows one part falls short of the scope. "
                   "A 70/30 split pays for the work delivered and gives the customer enough to fix the rest.",
    "SPLIT_50_50": "The evidence supports parts of both accounts and does not show clearly how much of the agreed scope was met, so the payment is split evenly.",
    "REFUND_FULL": "There is no evidence that the agreed work was delivered, so the customer is refunded in full.",
}
