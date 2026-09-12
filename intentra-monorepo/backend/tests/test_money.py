"""Money is integers all the way down; conversion and splits never lose a unit (schematics §4.5)."""
import pytest

from app.core.money import BPS, kobo_to_micro_usdc, micro_usdc_to_kobo, naira_to_kobo, split, within_tolerance
from app.core.remedies import REMEDY_BPS, Remedy

RATE = 1650


def test_the_demo_quote_converts_to_one_hundred_usdc():
    assert naira_to_kobo(165_000) == 16_500_000
    assert kobo_to_micro_usdc(16_500_000, RATE) == 100_000_000


def test_the_hard_cap_converts_as_documented():
    assert kobo_to_micro_usdc(naira_to_kobo(250_000), RATE) == 151_515_151


def test_the_seventy_thirty_split_matches_the_demo():
    to_provider, to_customer = split(100_000_000, REMEDY_BPS[Remedy.SPLIT_70_30])
    assert (to_provider, to_customer) == (70_000_000, 30_000_000)


@pytest.mark.parametrize("amount", [1, 3, 7, 999, 1_000_001, 100_000_000, 151_515_151, 987_654_321])
@pytest.mark.parametrize("bps", [0, 1, 4_999, 5_000, 7_000, 9_999, 10_000])
def test_a_split_always_adds_back_up(amount: int, bps: int):
    to_provider, to_customer = split(amount, bps)
    assert to_provider + to_customer == amount
    assert to_provider >= 0 and to_customer >= 0
    assert to_provider == amount * bps // BPS


def test_every_remedy_has_a_fixed_share():
    assert REMEDY_BPS == {Remedy.RELEASE_FULL: 10_000, Remedy.SPLIT_70_30: 7_000,
                          Remedy.SPLIT_50_50: 5_000, Remedy.REFUND_FULL: 0}


def test_an_out_of_range_share_is_refused():
    with pytest.raises(ValueError):
        split(100, 10_001)


def test_the_tolerance_band_includes_exactly_ten_percent():
    authorized = kobo_to_micro_usdc(naira_to_kobo(180_000), RATE)
    assert within_tolerance(kobo_to_micro_usdc(naira_to_kobo(198_000), RATE), authorized, 1000)
    assert not within_tolerance(kobo_to_micro_usdc(naira_to_kobo(220_000), RATE), authorized, 1000)


@pytest.mark.parametrize("kobo", [100, 16_500_000, 25_000_000])
def test_conversion_round_trips_within_a_kobo(kobo: int):
    assert abs(micro_usdc_to_kobo(kobo_to_micro_usdc(kobo, RATE), RATE) - kobo) <= 1
