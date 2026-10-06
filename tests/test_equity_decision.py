import pytest

from equity_decision import (EquityConfig, MarketContext, brier_score, decide,
                             edge_pct, expected_calibration_error,
                             kelly_fraction)

CFG = EquityConfig()


def test_edge_sign_and_validation():
    assert edge_pct(0.6, 0.5) == pytest.approx(10.0)
    assert edge_pct(0.4, 0.5) == pytest.approx(-10.0)
    assert edge_pct(0.5, 0.5) == 0.0
    with pytest.raises(ValueError):
        edge_pct(1.1, 0.5)
    with pytest.raises(ValueError):
        edge_pct(0.5, -0.1)


def test_kelly_positive_and_zero():
    # b=1, p=0.6 -> f = (0.6-0.4)/1 = 0.2
    assert kelly_fraction(0.6, 0.5) == pytest.approx(0.2)
    assert kelly_fraction(0.5, 0.5) == 0.0
    assert kelly_fraction(0.4, 0.5) == 0.0


def test_kelly_boundaries():
    assert kelly_fraction(0.6, 0.0) == 0.0
    assert kelly_fraction(0.6, 1.0) == 0.0
    with pytest.raises(ValueError):
        kelly_fraction(0.6, 1.5)


def test_decide_buy():
    d = decide(CFG, 0.60, 0.50)
    assert d.action == "BUY"
    assert d.position_fraction == pytest.approx(0.05)  # 0.25 * 0.2
    assert d.conviction == "high"
    assert d.probabilities["BUY"] > d.probabilities["HOLD"] > d.probabilities["SELL"]


def test_decide_sell():
    d = decide(CFG, 0.40, 0.50)
    assert d.action == "SELL"
    assert d.edge_pct == pytest.approx(-10.0)
    assert d.position_fraction == pytest.approx(0.05)
    assert d.probabilities["SELL"] > d.probabilities["BUY"]


def test_decide_hold_and_zero_edge():
    d = decide(CFG, 0.52, 0.50)
    assert d.action == "HOLD" and d.position_fraction == 0.0 and d.conviction == "none"
    z = decide(CFG, 0.5, 0.5)
    assert z.action == "HOLD" and z.edge_pct == 0.0


def test_momentum_confirm_vs_adverse_flips_outcome():
    # edge 2.5pp: base req 3.0 -> HOLD
    assert decide(CFG, 0.525, 0.50).action == "HOLD"
    confirm = decide(CFG, 0.525, 0.50, MarketContext(momentum=0.02))
    assert confirm.required_edge_pct == pytest.approx(2.0)
    assert confirm.action == "BUY"
    # edge 4pp: base BUY, adverse momentum (req 4.5) -> HOLD
    assert decide(CFG, 0.54, 0.50).action == "BUY"
    adverse = decide(CFG, 0.54, 0.50, MarketContext(momentum=-0.02))
    assert adverse.required_edge_pct == pytest.approx(4.5)
    assert adverse.action == "HOLD"


def test_momentum_for_sell_side():
    d = decide(CFG, 0.48, 0.50, MarketContext(momentum=-0.02))  # -2pp, req 2.0
    assert d.action == "SELL"


def test_high_vol_bump():
    d = decide(CFG, 0.535, 0.50, MarketContext(realized_vol=0.5))
    assert d.required_edge_pct == pytest.approx(4.0)
    assert d.action == "HOLD"
    calm = decide(CFG, 0.535, 0.50, MarketContext(realized_vol=0.2))
    assert calm.action == "BUY"


def test_edge_floor_clamp():
    cfg = EquityConfig(min_edge_pct=1.5, momentum_confirm_discount_pct=5.0)
    d = decide(cfg, 0.52, 0.50, MarketContext(momentum=1.0))
    assert d.required_edge_pct == pytest.approx(cfg.edge_floor_pct)
    assert d.action == "BUY"


def test_position_cap():
    d = decide(CFG, 0.90, 0.50)
    assert d.action == "BUY"
    assert d.position_fraction == pytest.approx(CFG.max_position_fraction)


def test_conviction_tiers():
    assert decide(CFG, 0.54, 0.50).conviction == "low"
    assert decide(CFG, 0.58, 0.50).conviction == "high"
    assert decide(CFG, 0.51, 0.50).conviction == "none"


@pytest.mark.parametrize("fair,mkt", [(0.6, 0.5), (0.5, 0.5), (0.3, 0.6)])
def test_probabilities_sum_to_one(fair, mkt):
    d = decide(CFG, fair, mkt)
    assert sum(d.probabilities.values()) == pytest.approx(1.0, abs=1e-3)


def test_sell_with_market_one_is_hold_not_zero_size_sell():
    d = decide(CFG, 0.5, 1.0)  # edge -50pp, SELL Kelly uses 1-market = 0
    assert d.action == "HOLD"
    assert d.position_fraction == 0.0
    assert "Kelly size is 0" in d.rationale


def test_buy_with_market_zero_is_hold():
    d = decide(CFG, 0.5, 0.0)
    assert d.action == "HOLD" and d.position_fraction == 0.0


def test_no_zero_size_trades():
    for fair in (0.0, 0.25, 0.5, 0.75, 1.0):
        for mkt in (0.0, 0.25, 0.5, 0.75, 1.0):
            d = decide(CFG, fair, mkt)
            if d.action != "HOLD":
                assert d.position_fraction > 0


def test_str():
    assert str(decide(CFG, 0.6, 0.5)).startswith("BUY")


def test_brier():
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert brier_score([0.5, 0.5], [1, 0]) == pytest.approx(0.25)
    assert brier_score([0.6, 0.55, 0.7, 0.3, 0.8], [1, 0, 1, 0, 1]) == pytest.approx(
        (0.16 + 0.3025 + 0.09 + 0.09 + 0.04) / 5)


def test_ece():
    assert expected_calibration_error([1.0, 0.0], [1, 0]) == 0.0
    # all in one bin: conf 0.7, acc 0.5
    assert expected_calibration_error([0.7, 0.7], [1, 0]) == pytest.approx(0.2)
    assert expected_calibration_error([1.0], [1]) == 0.0  # p=1.0 -> last bin


@pytest.mark.parametrize("fn", [brier_score, expected_calibration_error])
def test_calibration_errors(fn):
    with pytest.raises(ValueError):
        fn([], [])
    with pytest.raises(ValueError):
        fn([0.5], [1, 0])


def test_conviction_boundary_float_tolerance():
    # (0.62 - 0.54) * 100 is 7.999...99 in floating point; must count as strong.
    assert decide(CFG, 0.62, 0.54).conviction == "high"
