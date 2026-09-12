"""Every state has words for both parties, and status_line picks the right one."""
from app.core.explanation import status_line
from app.core.status_copy import CANCELLED_REFUNDED, STATUS
from app.core.states import TxState


def test_every_state_has_copy_for_both_roles():
    """The state machine and the copy table are edited separately; this is what keeps them in step."""
    assert set(STATUS) == set(TxState)
    for state, (customer, provider) in STATUS.items():
        assert customer and provider, state


def test_status_line_picks_the_line_for_the_role():
    customer, provider = STATUS[TxState.FUNDED]
    assert status_line(TxState.FUNDED, "customer") == customer
    assert status_line(TxState.FUNDED, "provider") == provider


def test_a_refund_explains_itself_but_a_plain_cancellation_does_not():
    assert status_line(TxState.CANCELLED, "customer", close_reason="refunded") == CANCELLED_REFUNDED
    assert status_line(TxState.CANCELLED, "customer") == STATUS[TxState.CANCELLED][0]


def test_an_unknown_state_renders_empty_rather_than_raising():
    """A state added to the machine without copy must not 500 a screen."""
    assert status_line("NOT_A_STATE", "customer") == ""
