"""Plain-language status lines and fallback texts. Templates first, so every screen has words even when the model is unavailable."""

STATUS = {
    "CREATED": ("Tell us what you need done.", "—"),
    "INTENT_STRUCTURED": ("Pick a provider to continue.", "—"),
    "QUOTE_SELECTED": ("Review the job and approve the payment.", "Waiting for the customer to approve."),
    "AWAITING_AUTHORIZATION": ("Review the job and approve the payment.", "Waiting for the customer to approve."),
    "AUTHORIZED": ("Approved. Fund the escrow to protect the payment.", "Approved. Waiting for the customer to fund the escrow."),
    "FUNDING": ("Confirming your payment on Arc…", "Confirming the customer's payment on Arc…"),
    "FUNDED": ("Payment protected. Your provider can start.", "The money is locked in escrow. You can start the job."),
    "IN_PROGRESS": ("The job is in progress.", "Upload an after-photo for each room when you finish."),
    "EVIDENCE_SUBMITTED": ("Your provider is uploading proof of the work.", "Add the remaining photos, then mark the job delivered."),
    "DELIVERED": ("The job is marked done. Release the payment, or report a problem before the window closes.",
                  "Delivered. The payment releases when the customer confirms or the window closes."),
    "RELEASED": ("Payment released to your provider.", "Payment released to you."),
    "DISPUTED": ("The payment is frozen while your complaint is reviewed.", "The customer reported a problem. Respond with your side and any photos."),
    "RESOLVING": ("Intentra is reviewing both sides.", "Intentra is reviewing both sides."),
    "PROPOSED": ("A resolution is ready. Review it and sign, or reject it.", "A resolution is ready. Review it and sign, or reject it."),
    "SETTLED": ("Settled on Arc as both of you agreed.", "Settled on Arc as both of you agreed."),
    "ESCALATED": ("A person from Intentra will review this. The money stays frozen.", "A person from Intentra will review this. The money stays frozen."),
    "CANCELLED": ("This job was cancelled.", "This job was cancelled."),
}


def status_line(state: str, role: str, close_reason: str | None = None) -> str:
    if state == "CANCELLED" and close_reason == "refunded":
        return "The escrow refunded the customer because the job was not delivered in time."
    customer, provider = STATUS.get(state, ("", ""))
    return provider if role == "provider" else customer


def naira(minor: int) -> str:
    return f"₦{minor // 100:,}"


def rec_text(quote: dict, request: dict) -> dict:
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


RATIONALES = {
    "RELEASE_FULL": "The provider's photos cover every item in the agreed scope and the complaint does not show missing work, so the full payment goes to the provider.",
    "SPLIT_70_30": "The after-photos show most of the agreed work was done, and the complaint credibly shows one part falls short of the scope. "
                   "A 70/30 split pays for the work delivered and gives the customer enough to fix the rest.",
    "SPLIT_50_50": "The evidence supports parts of both accounts and does not show clearly how much of the agreed scope was met, so the payment is split evenly.",
    "REFUND_FULL": "There is no evidence that the agreed work was delivered, so the customer is refunded in full.",
}
