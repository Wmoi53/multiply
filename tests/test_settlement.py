"""Exhaustive Asian-Handicap settlement tests.

Covers whole / half / quarter lines on both sides, the sign convention, and the
profit-unit conversion in ``settle_bet`` (including PASS decisions).
"""

from types import SimpleNamespace

import pytest

from backtest.data import BacktestFixture
from backtest.settlement import ah_result, settle_bet


def _fx(line, hg, ag, home_odds=2.0, away_odds=2.0):
    return BacktestFixture(
        label="x",
        home_odds=home_odds,
        away_odds=away_odds,
        fair_home=0.5,
        fair_away=0.5,
        line=line,
        home_goals=hg,
        away_goals=ag,
    )


def _bet(side):
    return SimpleNamespace(action="BET", side=side)


# ---------------------------------------------------------------------------
# ah_result -- WHOLE lines (win / push / loss)
# ---------------------------------------------------------------------------
def test_whole_line_zero_home():
    assert ah_result("home", 0.0, 2, 1) == 1.0   # home win
    assert ah_result("home", 0.0, 1, 1) == 0.0   # draw -> push
    assert ah_result("home", 0.0, 0, 1) == -1.0  # home loss


def test_whole_line_minus_one_home():
    assert ah_result("home", -1.0, 2, 0) == 1.0   # win by 2 covers -1
    assert ah_result("home", -1.0, 1, 0) == 0.0   # win by exactly 1 -> push
    assert ah_result("home", -1.0, 1, 1) == -1.0  # draw -> loss


def test_whole_line_plus_one_home():
    assert ah_result("home", 1.0, 1, 1) == 1.0    # draw +1 -> win
    assert ah_result("home", 1.0, 0, 1) == 0.0    # lose by 1 -> push
    assert ah_result("home", 1.0, 0, 2) == -1.0   # lose by 2 -> loss


# ---------------------------------------------------------------------------
# ah_result -- HALF lines (win / loss only, never a push)
# ---------------------------------------------------------------------------
def test_half_line_minus_half_home():
    assert ah_result("home", -0.5, 1, 0) == 1.0
    assert ah_result("home", -0.5, 0, 0) == -1.0


def test_half_line_minus_one_and_half_home():
    assert ah_result("home", -1.5, 2, 0) == 1.0   # win by 2 covers -1.5
    assert ah_result("home", -1.5, 1, 0) == -1.0  # win by 1 does not


def test_half_line_plus_half_home():
    assert ah_result("home", 0.5, 0, 0) == 1.0    # draw +0.5 -> win
    assert ah_result("home", 0.5, 0, 1) == -1.0   # lose by 1 -> loss


# ---------------------------------------------------------------------------
# ah_result -- QUARTER lines (half-win / half-loss / full outcomes)
# ---------------------------------------------------------------------------
def test_quarter_minus_025_home():
    assert ah_result("home", -0.25, 2, 1) == 1.0    # win -> full win
    assert ah_result("home", -0.25, 1, 1) == -0.5   # draw -> half loss
    assert ah_result("home", -0.25, 0, 1) == -1.0   # loss -> full loss


def test_quarter_minus_075_home():
    assert ah_result("home", -0.75, 3, 1) == 1.0    # win by 2 -> full win
    assert ah_result("home", -0.75, 2, 1) == 0.5    # win by 1 -> half win
    assert ah_result("home", -0.75, 1, 1) == -1.0   # draw -> full loss


def test_quarter_plus_025_home():
    assert ah_result("home", 0.25, 1, 0) == 1.0     # win -> full win
    assert ah_result("home", 0.25, 1, 1) == 0.5     # draw -> half win
    assert ah_result("home", 0.25, 0, 1) == -1.0    # lose by 1 -> full loss


def test_quarter_plus_075_home():
    assert ah_result("home", 0.75, 1, 1) == 1.0     # draw +0.75 -> full win
    assert ah_result("home", 0.75, 0, 1) == -0.5    # lose by 1 -> half loss
    assert ah_result("home", 0.75, 0, 2) == -1.0    # lose by 2 -> full loss


# ---------------------------------------------------------------------------
# Sign convention: away is the mirror of home on the same score.
# ---------------------------------------------------------------------------
def test_away_side_mirrors_home():
    # score 1-0: home wins outright. Home -0.5 wins; away +0.5 (home line -0.5) loses.
    assert ah_result("home", -0.5, 1, 0) == 1.0
    assert ah_result("away", -0.5, 1, 0) == -1.0


def test_away_side_quarter_half_loss():
    # home line +0.25 -> away handicap -0.25; a draw makes the away back a half loss.
    assert ah_result("away", 0.25, 1, 1) == -0.5


def test_away_whole_line_win():
    # away wins outright at level line 0.0 (score 1-2).
    assert ah_result("away", 0.0, 1, 2) == 1.0


def test_bad_side_raises():
    with pytest.raises(ValueError):
        ah_result("draw", 0.0, 1, 1)


# ---------------------------------------------------------------------------
# settle_bet -- profit in units for a 1-unit stake
# ---------------------------------------------------------------------------
def test_settle_full_win_uses_odds():
    assert settle_bet(_bet("home"), _fx(-0.5, 1, 0, home_odds=2.0)) == pytest.approx(1.0)
    assert settle_bet(_bet("home"), _fx(-0.5, 1, 0, home_odds=1.5)) == pytest.approx(0.5)


def test_settle_half_win_uses_half_odds():
    # -0.75, win by 1 -> half win.
    assert settle_bet(_bet("home"), _fx(-0.75, 2, 1, home_odds=2.0)) == pytest.approx(0.5)
    assert settle_bet(_bet("home"), _fx(-0.75, 2, 1, home_odds=1.5)) == pytest.approx(0.25)


def test_settle_push_returns_zero():
    assert settle_bet(_bet("home"), _fx(0.0, 1, 1, home_odds=2.0)) == 0.0


def test_settle_half_loss_is_minus_half():
    # -0.25, draw -> half loss (odds do not matter for the loss leg).
    assert settle_bet(_bet("home"), _fx(-0.25, 1, 1, home_odds=2.0)) == pytest.approx(-0.5)
    assert settle_bet(_bet("home"), _fx(-0.25, 1, 1, home_odds=1.5)) == pytest.approx(-0.5)


def test_settle_full_loss_is_minus_one():
    assert settle_bet(_bet("home"), _fx(-0.5, 0, 1, home_odds=2.0)) == pytest.approx(-1.0)


def test_settle_uses_away_odds_for_away_bet():
    # away full win at away_odds 2.5 -> profit 1.5
    fx = _fx(0.0, 1, 2, home_odds=1.5, away_odds=2.5)
    assert settle_bet(_bet("away"), fx) == pytest.approx(1.5)


def test_settle_pass_not_settled():
    pass_decision = SimpleNamespace(action="PASS", side=None)
    assert settle_bet(pass_decision, _fx(-0.5, 1, 0)) == 0.0


def test_settle_bet_with_no_side_not_settled():
    no_side = SimpleNamespace(action="BET", side=None)
    assert settle_bet(no_side, _fx(-0.5, 1, 0)) == 0.0
