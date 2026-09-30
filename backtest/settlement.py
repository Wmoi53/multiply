"""Asian-Handicap settlement.

Settles a bet against a final score using the engine's own line convention:
``line`` is the **home-side** handicap. The away side's handicap is the
negation of ``line``. A side "covers" when its own goal difference plus its own
handicap is positive.

``ah_result`` returns a canonical outcome multiplier in the set
``{1.0, 0.5, 0.0, -0.5, -1.0}``:

    +1.0  full win   (whole stake won)
    +0.5  half win   (half stake won, half pushed)
     0.0  push       (stake returned)
    -0.5  half loss  (half stake lost, half pushed)
    -1.0  full loss  (whole stake lost)

Line handling:

* Whole lines  (0, ±1, ±2 ...): win / push / loss.
* Half lines   (±0.5, ±1.5 ...): win / loss only (a half-goal margin can never
  land on zero).
* Quarter lines (±0.25, ±0.75 ...): the stake is split across the two adjacent
  half/whole lines (``hcap - 0.25`` and ``hcap + 0.25``); each half settles
  independently and the results are averaged -> enables half-win and half-loss.

``settle_bet`` converts that outcome into profit for a **1-unit** stake at the
bet side's decimal odds:

    full win  -> +(odds - 1)
    half win  -> +(odds - 1) / 2
    push      ->  0
    half loss -> -0.5
    full loss -> -1
"""

from __future__ import annotations

__all__ = ["ah_result", "settle_bet"]


def _own_handicap(side: str, line: float) -> float:
    """The chosen side's own handicap (home keeps ``line``; away negates it)."""
    if side == "home":
        return line
    if side == "away":
        return -line
    raise ValueError(f"side must be 'home' or 'away', got {side!r}")


def _own_goal_diff(side: str, home_goals: int, away_goals: int) -> int:
    """Goal difference from the chosen side's own perspective."""
    if side == "home":
        return home_goals - away_goals
    if side == "away":
        return away_goals - home_goals
    raise ValueError(f"side must be 'home' or 'away', got {side!r}")


def _settle_simple(adjusted: float) -> float:
    """Settle a whole- or half-line sub-bet given the adjusted margin.

    ``adjusted`` is (own goal difference + own handicap). Positive covers,
    exactly zero is a push (only reachable on whole lines), negative loses.
    """
    if adjusted > 0:
        return 1.0
    if adjusted < 0:
        return -1.0
    return 0.0


def ah_result(side: str, line: float, home_goals: int, away_goals: int) -> float:
    """Asian-Handicap outcome multiplier for ``side`` at ``line``.

    Returns one of ``{1.0, 0.5, 0.0, -0.5, -1.0}`` (see module docstring).
    """
    hcap = _own_handicap(side, line)
    gd = _own_goal_diff(side, home_goals, away_goals)

    # Classify the line by quarters: q = hcap * 4 (rounded to shake off float
    # noise). q % 4 == 0 -> whole; q even (not %4) -> half; q odd -> quarter.
    q = round(hcap * 4)
    if q % 4 == 0:
        return _settle_simple(gd + hcap)
    if q % 2 == 0:
        # Half line: never lands on a push.
        return _settle_simple(gd + hcap)

    # Quarter line: split the stake across the two adjacent lines.
    lower = _settle_simple(gd + (hcap - 0.25))
    upper = _settle_simple(gd + (hcap + 0.25))
    return (lower + upper) / 2.0


def settle_bet(decision, fixture) -> float:
    """Profit (in units) of a **1-unit** stake for ``decision`` on ``fixture``.

    Only settles when ``decision.action == 'BET'``; a PASS (or a bet with no
    side) returns 0.0 -- nothing was staked. The profit uses the chosen side's
    decimal odds:

        full win  -> +(odds - 1)
        half win  -> +(odds - 1) / 2
        push      ->  0
        half loss -> -0.5
        full loss -> -1
    """
    if getattr(decision, "action", None) != "BET" or decision.side is None:
        return 0.0

    odds = fixture.odds_for(decision.side)
    r = ah_result(
        decision.side, fixture.line, fixture.home_goals, fixture.away_goals
    )

    if r > 0:
        # Win portion pays at the price; +1.0 -> (odds-1), +0.5 -> (odds-1)/2.
        return r * (odds - 1.0)
    # r <= 0: push returns 0.0; half/full loss are exactly r (-0.5 / -1.0).
    return r
