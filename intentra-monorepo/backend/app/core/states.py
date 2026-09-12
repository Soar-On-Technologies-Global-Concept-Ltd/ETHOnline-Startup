"""Transaction lifecycle (Blueprint §13, reconciled with the PRD).

This module is the whole truth about which states exist and which moves are legal. It is pure data and one lookup:
no I/O, no database, no web framework, so the rules can be read and tested on their own. The only code allowed to
write transactions.state is app/domains/transactions/machine.py, enforced by tests/test_single_writer.py.
The words shown to users for each state live in app/core/status_copy.py.
"""
from enum import StrEnum


class TxState(StrEnum):
    """Where a transaction is now. Stored verbatim in transactions.state."""
    CREATED = "CREATED"
    INTENT_STRUCTURED = "INTENT_STRUCTURED"
    QUOTE_SELECTED = "QUOTE_SELECTED"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    FUNDING = "FUNDING"
    FUNDED = "FUNDED"
    IN_PROGRESS = "IN_PROGRESS"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    DELIVERED = "DELIVERED"
    RELEASED = "RELEASED"
    DISPUTED = "DISPUTED"
    RESOLVING = "RESOLVING"
    PROPOSED = "PROPOSED"
    SETTLED = "SETTLED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class Event(StrEnum):
    """What happened. Names ending in _ONCHAIN are only raised by the watcher after a confirmed escrow log,
    which is how money states stay tied to the chain rather than to an API call."""
    INTENT_STRUCTURED = "INTENT_STRUCTURED"
    QUOTE_SELECTED = "QUOTE_SELECTED"
    AUTHORIZATION_ISSUED = "AUTHORIZATION_ISSUED"
    AUTHORIZED = "AUTHORIZED"
    FUNDING_STARTED = "FUNDING_STARTED"
    FUNDED_ONCHAIN = "FUNDED_ONCHAIN"
    WORK_STARTED = "WORK_STARTED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    DELIVERY_MARKED = "DELIVERY_MARKED"
    RELEASED_ONCHAIN = "RELEASED_ONCHAIN"
    DISPUTE_OPENED_ONCHAIN = "DISPUTE_OPENED_ONCHAIN"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    RESPONSE_TIMEOUT = "RESPONSE_TIMEOUT"
    PROPOSAL_MADE = "PROPOSAL_MADE"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    SETTLED_ONCHAIN = "SETTLED_ONCHAIN"
    REJECTED = "REJECTED"
    ACCEPT_TIMEOUT = "ACCEPT_TIMEOUT"
    DECLINED = "DECLINED"
    AUTHORIZATION_EXPIRED = "AUTHORIZATION_EXPIRED"
    REFUNDED_ONCHAIN = "REFUNDED_ONCHAIN"


S, E = TxState, Event   # local shorthand; the table below is read as a grid, so short names keep rows on one line

# (current state, event) -> next state. A pair that is absent is illegal: there is no default and no fallthrough,
# so a new move has to be added here deliberately. tests/test_transitions.py checks every other pair is refused.
TRANSITIONS: dict[tuple[TxState, Event], TxState] = {
    (S.CREATED, E.INTENT_STRUCTURED): S.INTENT_STRUCTURED,
    (S.INTENT_STRUCTURED, E.QUOTE_SELECTED): S.QUOTE_SELECTED,
    (S.QUOTE_SELECTED, E.AUTHORIZATION_ISSUED): S.AWAITING_AUTHORIZATION,
    (S.AWAITING_AUTHORIZATION, E.AUTHORIZED): S.AUTHORIZED,
    (S.AUTHORIZED, E.FUNDING_STARTED): S.FUNDING,
    (S.FUNDING, E.FUNDED_ONCHAIN): S.FUNDED,
    (S.FUNDED, E.WORK_STARTED): S.IN_PROGRESS,
    (S.IN_PROGRESS, E.EVIDENCE_ADDED): S.EVIDENCE_SUBMITTED,
    (S.EVIDENCE_SUBMITTED, E.DELIVERY_MARKED): S.DELIVERED,
    (S.DELIVERED, E.RELEASED_ONCHAIN): S.RELEASED,
    (S.DELIVERED, E.DISPUTE_OPENED_ONCHAIN): S.DISPUTED,
    (S.DISPUTED, E.RESPONSE_RECEIVED): S.RESOLVING,
    (S.DISPUTED, E.RESPONSE_TIMEOUT): S.RESOLVING,
    (S.RESOLVING, E.PROPOSAL_MADE): S.PROPOSED,
    (S.RESOLVING, E.ESCALATION_REQUIRED): S.ESCALATED,
    (S.PROPOSED, E.SETTLED_ONCHAIN): S.SETTLED,
    (S.PROPOSED, E.REJECTED): S.ESCALATED,
    (S.PROPOSED, E.ACCEPT_TIMEOUT): S.ESCALATED,
}
# A funding tx that reverts or never lands can still be cancelled; so can anything before money moves.
for _state in (S.CREATED, S.INTENT_STRUCTURED, S.QUOTE_SELECTED, S.AWAITING_AUTHORIZATION, S.AUTHORIZED, S.FUNDING):
    TRANSITIONS[(_state, E.DECLINED)] = S.CANCELLED
    TRANSITIONS[(_state, E.AUTHORIZATION_EXPIRED)] = S.CANCELLED
# The escrow returned the money without a resolution. Reserved for executeAbandonment: as of today the watcher
# records that as a note and a close_reason rather than a transition, so nothing raises REFUNDED_ONCHAIN yet.
for _state in (S.FUNDED, S.IN_PROGRESS, S.EVIDENCE_SUBMITTED):
    TRANSITIONS[(_state, E.REFUNDED_ONCHAIN)] = S.CANCELLED

# End states: nothing leaves these, so the machine refuses any further event.
TERMINAL: frozenset[TxState] = frozenset({S.RELEASED, S.SETTLED, S.CANCELLED})
# Events the API may never raise by itself — each one needs a confirmed escrow log behind it.
CHAIN_COMMITTED: frozenset[Event] = frozenset({E.FUNDED_ONCHAIN, E.RELEASED_ONCHAIN,
                                              E.DISPUTE_OPENED_ONCHAIN, E.SETTLED_ONCHAIN, E.REFUNDED_ONCHAIN})
# Before any money is at stake, so these are safe to abandon and are excluded from a provider's trust counts.
PRE_FUNDING: frozenset[TxState] = frozenset({S.CREATED, S.INTENT_STRUCTURED, S.QUOTE_SELECTED, S.AWAITING_AUTHORIZATION, S.AUTHORIZED, S.FUNDING})


def next_state(state: TxState, event: Event) -> TxState | None:
    """The state this event moves us to, or None if the move is not allowed from here.

    Returning None rather than raising lets callers ask "is this legal?" and answer the caller cleanly,
    instead of using an exception for an ordinary refusal.
    """
    return TRANSITIONS.get((state, event))


class Role(StrEnum):
    """Who is acting. OPERATOR is Intentra staff on the escalation path, never a party to the escrow."""
    CUSTOMER = "customer"
    PROVIDER = "provider"
    OPERATOR = "operator"


class EvidenceKind(StrEnum):
    """What a piece of evidence is for. Each kind is accepted from one role in one set of states;
    app/domains/evidence/service.py holds that table."""
    AFTER_PHOTO = "AFTER_PHOTO"
    COMPLAINT = "COMPLAINT"
    COUNTER = "COUNTER"


class ComplaintCategory(StrEnum):
    """The fixed set a customer may choose from. Free text goes in the complaint body, not here, so the
    dispute ladder can reason over a closed set."""
    INCOMPLETE = "INCOMPLETE"
    NOT_AS_AGREED = "NOT_AS_AGREED"
    DAMAGE = "DAMAGE"
    NO_SHOW = "NO_SHOW"
