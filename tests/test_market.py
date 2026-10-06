import math

import pytest

from ah_decision.market import (
    devig_proportional,
    edge_pct,
    implied_prob,
    kelly_fraction,
    overround,
    overround_pct,
)


def test_implied_prob_basic():
    assert implied_prob(2.0) == pytest.approx(0.5)
    assert implied_prob(4.0) == pytest.approx(0.25)
    assert implied_prob(1.25) == pytest.approx(0.8)


def test_overround_and_pct():
    # 1.90 / 2.05 two-way market has a small vig.
    o = overround(1.90, 2.05)
    assert o > 1.0
    assert o == pytest.approx(1.0 / 1.90 + 1.0 / 2.05)
    assert overround_pct(1.90, 2.05) == pytest.approx((o - 1.0) * 100.0)
    # A perfectly fair 2.0/2.0 market has zero overround.
    assert overround_pct(2.0, 2.0) == pytest.approx(0.0)


def test_devig_sums_to_one():
    probs = devig_proportional([1.90, 2.05])
    assert sum(probs) == pytest.approx(1.0)
    assert len(probs) == 2
    # Shorter price -> larger fair prob.
    assert probs[0] > probs[1]


def test_devig_three_way_sums_to_one():
    probs = devig_proportional([2.5, 3.4, 3.0])
    assert sum(probs) == pytest.approx(1.0)


def test_edge_pct_sign():
    # Fair prob above implied -> positive edge (value).
    assert edge_pct(0.60, 2.0) == pytest.approx((0.60 - 0.5) * 100.0)
    assert edge_pct(0.60, 2.0) > 0
    # Fair prob below implied -> negative edge.
    assert edge_pct(0.40, 2.0) < 0


def test_kelly_positive_edge():
    # p=0.6, odds=2.0 (b=1): f* = (1*0.6 - 0.4)/1 = 0.2
    assert kelly_fraction(0.6, 2.0) == pytest.approx(0.2)


def test_kelly_negative_edge_clamped():
    # No edge -> clamp to 0.
    assert kelly_fraction(0.4, 2.0) == 0.0
    assert kelly_fraction(0.3, 1.5) == 0.0


def test_kelly_zero_at_fair_price():
    # p exactly equals implied -> f* = 0.
    assert kelly_fraction(0.5, 2.0) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("bad", [1.0, 0.9, 0.0, -1.0])
def test_invalid_odds_raise(bad):
    with pytest.raises(ValueError):
        implied_prob(bad)


@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_invalid_prob_raises(bad):
    with pytest.raises(ValueError):
        edge_pct(bad, 2.0)
    with pytest.raises(ValueError):
        kelly_fraction(bad, 2.0)


def test_overround_requires_input():
    with pytest.raises(ValueError):
        overround()
    with pytest.raises(ValueError):
        devig_proportional([])
