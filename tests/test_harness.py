"""Backtest harness tests.

A small, hand-checkable fixture set with known scores drives assertions on bet
counts, hit rate, ROI, flat-vs-compound bankroll behaviour, PASS exclusion, and
the calibration / segment structures.
"""

import pytest

from ah_decision.conditions import OddsSnapshot
from ah_decision.config import Config
from backtest.data import BacktestFixture
from backtest.harness import run_backtest

CFG = Config()


def _fx(label, home_odds, away_odds, fair_home, fair_away, line, hg, ag, snaps=None):
    return BacktestFixture(
        label=label,
        home_odds=home_odds,
        away_odds=away_odds,
        fair_home=fair_home,
        fair_away=fair_away,
        line=line,
        home_goals=hg,
        away_goals=ag,
        snapshots=snaps or [],
    )


# A clear value bet on home that WINS (10% edge, evens price, level line).
_WIN = _fx("win", 2.0, 2.0, 0.60, 0.40, 0.0, 1, 0)
# The same value bet that LOSES.
_LOSS = _fx("loss", 2.0, 2.0, 0.60, 0.40, 0.0, 0, 1)
# No edge -> engine PASSes.
_PASS = _fx("pass", 2.0, 2.0, 0.505, 0.495, 0.0, 1, 0)
# Confirming-steam home bet that wins (mirrors engine's confirm scenario).
_STEAM = _fx(
    "steam",
    1.90,
    2.05,
    0.5463,
    0.4537,
    0.0,
    1,
    0,
    snaps=[
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.84, away_odds=2.00),
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
    ],
)


def test_pass_not_staked_or_settled():
    res = run_backtest(CFG, [_WIN, _PASS, _LOSS])
    assert res.n_fixtures == 3
    assert len(res.bets) == 2                      # PASS excluded
    assert all(b.label != "pass" for b in res.bets)


def test_counts_and_hit_rate():
    res = run_backtest(CFG, [_WIN, _LOSS, _PASS, _STEAM])
    s = res.summary()
    assert s["n_fixtures"] == 4
    assert s["n_bets"] == 3
    assert s["bet_rate"] == pytest.approx(3 / 4)
    assert s["wins"] == 2          # _WIN and _STEAM
    assert s["losses"] == 1        # _LOSS
    assert s["pushes"] == 0
    # decided = 3, hit_units = 2 -> 2/3
    assert s["hit_rate"] == pytest.approx(2 / 3)


def test_roi_matches_profit_over_staked():
    res = run_backtest(CFG, [_WIN, _LOSS, _STEAM])
    s = res.summary()
    assert s["total_staked"] > 0
    assert s["roi_pct"] == pytest.approx(
        s["total_profit"] / s["total_staked"] * 100.0
    )
    # _WIN stakes 0.05 and wins +0.05; _LOSS stakes 0.05 and loses -0.05; the
    # steam bet wins a little -> net positive.
    assert s["total_profit"] > 0


def test_flat_vs_compound_bankroll_differ():
    fixtures = [_WIN, _LOSS, _STEAM]
    flat = run_backtest(CFG, fixtures, bankroll_mode="flat", starting_bankroll=1.0)
    comp = run_backtest(CFG, fixtures, bankroll_mode="compound", starting_bankroll=1.0)
    assert flat.bankroll_mode == "flat"
    assert comp.bankroll_mode == "compound"
    # Same bets, different sizing over time -> different final bankroll.
    assert flat.final_bankroll != pytest.approx(comp.final_bankroll)
    # Flat: bankroll only reflects settled profits off a fixed base.
    assert flat.final_bankroll == pytest.approx(
        1.0 + flat.summary()["total_profit"]
    )


def test_compound_stakes_off_running_bankroll():
    # After a win the bankroll grows, so the next compound stake is larger than
    # the same bet's flat stake.
    fixtures = [_WIN, _WIN]
    comp = run_backtest(CFG, fixtures, bankroll_mode="compound")
    first, second = comp.bets
    assert second.stake_units > first.stake_units
    assert comp.final_bankroll > 1.0


def test_segments_and_calibration_populate():
    res = run_backtest(CFG, [_WIN, _LOSS, _STEAM])
    s = res.summary()

    seg = s["segments"]
    assert seg["by_side"]["home"]["n"] == 3
    assert seg["by_side"]["away"]["n"] == 0
    # Only the steam fixture carries a steam signal.
    assert seg["by_movement"]["steam"]["n"] == 1
    assert seg["by_movement"]["non_steam"]["n"] == 2
    # _WIN/_LOSS priced at evens (2.0) -> underdog bucket; _STEAM at 1.90 -> favorite.
    assert seg["by_price"]["favorite"]["n"] == 1
    assert seg["by_price"]["underdog"]["n"] == 2
    assert seg["by_line"]["deep"]["n"] == 0
    assert seg["by_line"]["shallow"]["n"] == 3

    # Calibration buckets present and total to the bet count.
    total = sum(b["n"] for b in s["edge_calibration"].values())
    assert total == s["n_bets"]


def test_invalid_bankroll_mode_raises():
    with pytest.raises(ValueError):
        run_backtest(CFG, [_WIN], bankroll_mode="martingale")
