"""Every legal transition is in the table, and every other state x event pair is refused (schematics §5.2)."""
import pytest

from app.core.states import PRE_FUNDING, TERMINAL, TRANSITIONS, Event, TxState, next_state

LEGAL = set(TRANSITIONS)


def test_the_table_matches_the_documented_count():
    assert len(TRANSITIONS) == 33


@pytest.mark.parametrize("state", list(TxState))
@pytest.mark.parametrize("event", list(Event))
def test_only_listed_pairs_are_allowed(state: TxState, event: Event):
    result = next_state(state, event)
    if (state, event) in LEGAL:
        assert result is TRANSITIONS[(state, event)]
    else:
        assert result is None


def test_the_happy_path_runs_end_to_end():
    state = TxState.CREATED
    for event in (Event.INTENT_STRUCTURED, Event.QUOTE_SELECTED, Event.AUTHORIZATION_ISSUED, Event.AUTHORIZED,
                  Event.FUNDING_STARTED, Event.FUNDED_ONCHAIN, Event.WORK_STARTED, Event.EVIDENCE_ADDED,
                  Event.DELIVERED_ONCHAIN, Event.RELEASED_ONCHAIN):
        state = next_state(state, event)
        assert state is not None
    assert state is TxState.RELEASED


def test_the_dispute_path_runs_end_to_end():
    state = TxState.DELIVERED
    for event in (Event.DISPUTE_OPENED_ONCHAIN, Event.RESPONSE_RECEIVED, Event.PROPOSAL_MADE, Event.SETTLED_ONCHAIN):
        state = next_state(state, event)
        assert state is not None
    assert state is TxState.SETTLED


def test_terminal_states_go_nowhere():
    for state in TERMINAL:
        assert all(next_state(state, event) is None for event in Event)


def test_every_pre_funding_state_can_be_cancelled():
    for state in PRE_FUNDING:
        assert next_state(state, Event.DECLINED) is TxState.CANCELLED
        assert next_state(state, Event.AUTHORIZATION_EXPIRED) is TxState.CANCELLED


def test_money_states_only_commit_on_chain_events():
    chain_only = {Event.FUNDED_ONCHAIN, Event.DELIVERED_ONCHAIN, Event.RELEASED_ONCHAIN, Event.DISPUTE_OPENED_ONCHAIN,
                  Event.SETTLED_ONCHAIN, Event.REFUNDED_ONCHAIN}
    money_states = {TxState.FUNDED, TxState.DELIVERED, TxState.RELEASED, TxState.DISPUTED, TxState.SETTLED}
    for (_, event), to in TRANSITIONS.items():
        if to in money_states:
            assert event in chain_only, f"{to} must commit on a chain event, not {event}"
