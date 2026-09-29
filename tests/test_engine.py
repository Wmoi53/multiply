import pytest

from ah_decision.conditions import OddsSnapshot, analyze_movement
from ah_decision.config import Config
from ah_decision.engine import Decision, decide, required_edge

CFG = Config()


# ---------------------------------------------------------------------------
# required_edge escalations
# ---------------------------------------------------------------------------
def test_required_edge_baseline():
    # mid-range price, no line, no movement -> baseline
    assert required_edge(CFG, 2.00, 0.0) == pytest.approx(CFG.min_abs_edge_pct)


def test_required_edge_short_favorite():
    # short favorite triggers price-skew floor
    assert required_edge(CFG, 1.60, 0.0) == pytest.approx(CFG.price_skew_edge_pct)


def test_required_edge_long_dog():
    assert required_edge(CFG, 2.50, 0.0) == pytest.approx(CFG.price_skew_edge_pct)


def test_required_edge_deep_line():
    # deep line but plain mid price -> deep-line floor
    assert required_edge(CFG, 2.00, -1.5) == pytest.approx(CFG.deep_line_edge_pct)


def test_required_edge_extreme_price():
    # very long price is both extreme and skewed -> at least extreme floor
    req = required_edge(CFG, 3.60, 0.0)
    assert req >= CFG.extreme_edge_pct


# ---------------------------------------------------------------------------
# market-condition adjustment to required_edge
# ---------------------------------------------------------------------------
def _confirming_steam_home():
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.84, away_odds=2.00),
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
    ]
    return analyze_movement(snaps, "home", CFG)


def _adverse_steam_home():
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.96, away_odds=1.98),
        OddsSnapshot(ts=120, home_odds=2.02, away_odds=1.92),
    ]
    return analyze_movement(snaps, "home", CFG)


def _confirming_nonsteam_home():
    # small confirming drift: shortened but below steam thresholds
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.88, away_odds=2.03),
        OddsSnapshot(ts=120, home_odds=1.86, away_odds=2.01),
    ]
    return analyze_movement(snaps, "home", CFG)


def test_confirming_move_lowers_bar():
    base = required_edge(CFG, 1.90, 0.0)
    confirmed = required_edge(CFG, 1.90, 0.0, _confirming_nonsteam_home())
    assert confirmed == pytest.approx(base - CFG.movement_confirm_discount_pct)


def test_confirming_steam_lowers_bar_more():
    m = _confirming_steam_home()
    assert m.is_steam is True
    confirmed = required_edge(CFG, 1.90, 0.0, m)
    expected = (
        CFG.min_abs_edge_pct
        - CFG.movement_confirm_discount_pct
        - CFG.steam_confirm_extra_pct
    )
    assert confirmed == pytest.approx(expected)


def test_adverse_move_raises_bar():
    m = _adverse_steam_home()
    assert m.is_steam is True
    adverse = required_edge(CFG, 1.90, 0.0, m)
    expected = (
        CFG.min_abs_edge_pct
        + CFG.movement_adverse_bump_pct
        + CFG.steam_adverse_extra_pct
    )
    assert adverse == pytest.approx(expected)


def test_required_edge_floor_clamp():
    cfg = Config(min_abs_edge_pct=0.7)
    # confirming steam discount (1.0) would push below the 0.5 floor
    m = _confirming_steam_home()
    assert required_edge(cfg, 1.90, 0.0, m) == pytest.approx(cfg.edge_floor_pct)


# ---------------------------------------------------------------------------
# decide()
# ---------------------------------------------------------------------------
def test_overround_gate_pass():
    d = decide(CFG, 0.60, 0.40, 1.85, 1.85, 0.0)
    assert d.action == "PASS"
    assert d.side is None
    assert "overround" in d.rationale.lower()


def test_clear_value_bet():
    # home fair 0.60 vs implied 0.50 -> 10% edge, mid price, no line
    d = decide(CFG, 0.60, 0.40, 2.00, 2.00, 0.0)
    assert d.action == "BET"
    assert d.side == "home"
    assert d.edge_pct == pytest.approx(10.0)
    assert d.stake_fraction > 0
    assert d.movement is None
    assert d.clv_proxy_pct == 0.0


def test_no_edge_pass():
    d = decide(CFG, 0.505, 0.495, 2.00, 2.00, 0.0)
    assert d.action == "PASS"
    assert d.side is None


def test_stake_clamped_to_max():
    # big edge -> quarter-Kelly would exceed max_stake_fraction
    d = decide(CFG, 0.65, 0.35, 2.00, 2.00, 0.0)
    assert d.action == "BET"
    assert d.stake_fraction == pytest.approx(CFG.max_stake_fraction)
    assert "clamped" in d.rationale.lower()


# The core improvement: same base scenario, opposite market conditions.
_BASE = dict(fair_home=0.5463, fair_away=0.4537, home_odds=1.90, away_odds=2.05, line=0.0)


def test_market_confirm_flips_to_bet():
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.84, away_odds=2.00),
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
    ]
    d = decide(CFG, snapshots=snaps, **_BASE)
    assert d.action == "BET"
    assert d.side == "home"
    assert d.movement is not None
    assert d.movement.direction == "shortened"


def test_market_drift_holds_pass():
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.96, away_odds=1.98),
        OddsSnapshot(ts=120, home_odds=2.02, away_odds=1.92),
    ]
    d = decide(CFG, snapshots=snaps, **_BASE)
    assert d.action == "PASS"
    assert d.movement is not None
    assert d.movement.direction == "drifted"


def test_base_scenario_bets_without_movement():
    # sanity: with no market data, the 2% edge clears the 1.5% baseline
    d = decide(CFG, **_BASE)
    assert d.action == "BET"
    assert d.side == "home"


def test_tie_breaker_favours_price_further_from_evens():
    # away has marginally larger edge but home price is further from 2.0;
    # within the tie-breaker band the further price (home) should be chosen.
    # home 1.80 (implied .5556), away 2.10 (implied .4762)
    fair_home = 1 / 1.80 + 0.048   # 4.8% edge
    fair_away = 1 / 2.10 + 0.050   # 5.0% edge
    d = decide(CFG, fair_home, fair_away, 1.80, 2.10, 0.0)
    assert d.action == "BET"
    assert d.side == "home"


def test_decision_str_is_readable():
    d = decide(CFG, 0.60, 0.40, 2.00, 2.00, 0.0)
    s = str(d)
    assert "BET" in s
    assert isinstance(d, Decision)
