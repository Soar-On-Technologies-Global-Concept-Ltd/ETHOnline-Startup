"""What each transaction state says to the two parties.

Copy only, kept apart from the state machine in states.py: that file decides which states exist and which moves are
legal, this one decides the words. Editing a sentence must never mean touching the machine, and vice versa.

Keys are TxState rather than plain strings, so a state renamed in states.py breaks this file at import instead of
silently rendering an empty line. StrEnum members hash as their value, so STATUS["FUNDED"] still works for callers
holding the raw column value. tests/test_status_copy.py proves every state is covered.
"""
from app.core.states import TxState

# (customer_line, provider_line). "—" means that role has nothing to do yet.
STATUS: dict[TxState, tuple[str, str]] = {
    TxState.CREATED: ("Tell us what you need done.", "—"),
    TxState.INTENT_STRUCTURED: ("Pick a provider to continue.", "—"),
    TxState.QUOTE_SELECTED: ("Review the job and approve the payment.", "Waiting for the customer to approve."),
    TxState.AWAITING_AUTHORIZATION: ("Review the job and approve the payment.", "Waiting for the customer to approve."),
    TxState.AUTHORIZED: ("Approved. Fund the escrow to protect the payment.", "Approved. Waiting for the customer to fund the escrow."),
    TxState.FUNDING: ("Confirming your payment on Arc…", "Confirming the customer's payment on Arc…"),
    TxState.FUNDED: ("Payment protected. Your provider can start.", "The money is locked in escrow. You can start the job."),
    TxState.IN_PROGRESS: ("The job is in progress.", "Upload an after-photo for each room when you finish."),
    TxState.EVIDENCE_SUBMITTED: ("Your provider is uploading proof of the work.", "Add the remaining photos, then mark the job delivered."),
    TxState.DELIVERED: ("The job is marked done. Release the payment, or report a problem before the window closes.",
                        "Delivered. The payment releases when the customer confirms or the window closes."),
    TxState.RELEASED: ("Payment released to your provider.", "Payment released to you."),
    TxState.DISPUTED: ("The payment is frozen while your complaint is reviewed.", "The customer reported a problem. Respond with your side and any photos."),
    TxState.RESOLVING: ("Intentra is reviewing both sides.", "Intentra is reviewing both sides."),
    TxState.PROPOSED: ("A resolution is ready. Review it and sign, or reject it.", "A resolution is ready. Review it and sign, or reject it."),
    TxState.SETTLED: ("Settled on Arc as both of you agreed.", "Settled on Arc as both of you agreed."),
    TxState.ESCALATED: ("A person from Intentra will review this. The money stays frozen.", "A person from Intentra will review this. The money stays frozen."),
    TxState.CANCELLED: ("This job was cancelled.", "This job was cancelled."),
}

# CANCELLED covers both a job nobody funded and a job the escrow refunded. Only the refund needs explaining.
CANCELLED_REFUNDED = "The escrow refunded the customer because the job was not delivered in time."
