import pytest

from ah_decision.conditions import (
    OddsSnapshot,
    analyze_movement,
    clv_proxy,
)
from ah_decision.config import Config

CFG = Config()


def _series_shortening():
    # home price shortens 1.90 -> 1.84 -> 1.78 (money on home)
    return [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.84, away_odds=2.00),
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
    ]


def test_shortened_direction_and_steam():
    m = analyze_movement(_series_shortening(), "home", CFG)
    assert m.side == "home"
    assert m.direction == "shortened"
    assert m.delta_implied_pct > 0
    # 1/1.78 - 1/1.90 ~ 3.55pp, above steam threshold 2.0
    assert m.delta_implied_pct == pytest.approx((1 / 1.78 - 1 / 1.90) * 100, rel=1e-6)
    assert m.is_steam is True
    assert m.clv_proxy_pct == pytest.approx(m.delta_implied_pct)


def test_velocity_is_last_step():
    m = analyze_movement(_series_shortening(), "home", CFG)
    expected = abs(1 / 1.78 - 1 / 1.84) * 100
    assert m.velocity == pytest.approx(expected, rel=1e-6)


def test_drifted_direction():
    # home drifts out 1.90 -> 2.02 (money leaving home)
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.96, away_odds=1.98),
        OddsSnapshot(ts=120, home_odds=2.02, away_odds=1.92),
    ]
    m = analyze_movement(snaps, "home", CFG)
    assert m.direction == "drifted"
    assert m.delta_implied_pct < 0


def test_stable_direction_no_steam():
    # tiny wiggle within the stable band
    snaps = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.00),
        OddsSnapshot(ts=60, home_odds=1.905, away_odds=1.995),
    ]
    m = analyze_movement(snaps, "home", CFG)
    assert m.direction == "stable"
    assert m.is_steam is False


def test_single_snapshot_edge_case():
    m = analyze_movement(
        [OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05)], "home", CFG
    )
    assert m.direction == "stable"
    assert m.is_steam is False
    assert m.velocity == 0.0
    assert m.delta_implied_pct == 0.0
    assert m.open_implied == m.current_implied


def test_empty_list_raises():
    with pytest.raises(ValueError):
        analyze_movement([], "home", CFG)


def test_bad_side_raises():
    with pytest.raises(ValueError):
        analyze_movement(_series_shortening(), "draw", CFG)


def test_snapshots_sorted_by_ts():
    # supply out of order; analyze should sort by ts before computing open/current
    snaps = [
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
    ]
    m = analyze_movement(snaps, "home", CFG)
    assert m.open_implied == pytest.approx(1 / 1.90)
    assert m.current_implied == pytest.approx(1 / 1.78)


def test_away_side_shortens_when_home_drifts():
    m = analyze_movement(_series_shortening(), "away", CFG)
    # away odds drift OUT (2.05 -> 1.95 is actually shortening for away)
    # away 2.05 -> 1.95 means away implied rises -> shortened
    assert m.direction == "shortened"


def test_clv_proxy_helper():
    # took 2.00, market now 1.80 -> positive CLV (beat the line)
    assert clv_proxy(2.00, 1.80) == pytest.approx((1 / 1.80 - 1 / 2.00) * 100)
    assert clv_proxy(2.00, 1.80) > 0
    # took 1.80, market now 2.00 -> negative CLV
    assert clv_proxy(1.80, 2.00) < 0
