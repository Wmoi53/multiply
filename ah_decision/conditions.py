"""Recent-market-conditions layer.

The improvement over a static odds snapshot: analyze a time-ordered series of
odds observations for a match to detect *how the market is moving* on a side.
We derive line movement, steam (sharp confirmed moves), and a closing-line-value
(CLV) proxy. The decision engine feeds these signals into the required-edge
calculation so bets ride confirming money and step aside from adverse drifts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .market import implied_prob

__all__ = [
    "OddsSnapshot",
    "MarketMovement",
    "analyze_movement",
    "clv_proxy",
]

_SIDES = ("home", "away")


@dataclass
class OddsSnapshot:
    """A single observation of the two-way price at time ``ts``.

    ``ts`` is a monotonically increasing sequence key -- we treat it as an
    epoch-style float (seconds). It is only used to order snapshots, so any
    consistent increasing numeric works.
    """

    ts: float
    home_odds: float
    away_odds: float

    def odds_for(self, side: str) -> float:
        _check_side(side)
        return self.home_odds if side == "home" else self.away_odds


@dataclass
class MarketMovement:
    """Summary of how the market moved on one side across the series."""

    side: str
    open_implied: float          # implied prob at first snapshot
    current_implied: float       # implied prob at last snapshot
    delta_implied_pct: float     # (current - open) * 100, in prob percentage points
    direction: str               # 'shortened' | 'drifted' | 'stable'
    is_steam: bool               # sharp confirmed move
    velocity: float              # |implied-prob change| over the most recent step, *100
    clv_proxy_pct: float         # closing-line-value proxy in percentage points


def _check_side(side: str) -> None:
    if side not in _SIDES:
        raise ValueError(f"side must be one of {_SIDES}, got {side!r}")


def clv_proxy(entry_odds: float, current_odds: float) -> float:
    """Closing-line-value proxy in percentage points.

    True CLV compares the price you took against the closing price. Pre-match
    the close is unknown, so we proxy it as how much the *current* implied
    probability has moved versus the *entry* price you would have taken:

        (implied(current) - implied(entry)) * 100

    Positive means the market has since shortened past your entry price -- you
    beat the line (good CLV). Negative means it drifted out (poor CLV).
    """
    return (implied_prob(current_odds) - implied_prob(entry_odds)) * 100.0


def analyze_movement(snapshots: list[OddsSnapshot], side: str, cfg) -> MarketMovement:
    """Analyze the movement of one side across a time-ordered snapshot series.

    ``delta_implied_pct`` = (current_implied - open_implied) * 100. Positive
    means the market is *shortening* the price on that side (money coming in /
    confirming); negative means it is *drifting* (money moving away).
    """
    _check_side(side)
    if not snapshots:
        raise ValueError("analyze_movement requires at least one snapshot")

    ordered = sorted(snapshots, key=lambda s: s.ts)
    first = ordered[0]
    last = ordered[-1]

    open_implied = implied_prob(first.odds_for(side))
    current_implied = implied_prob(last.odds_for(side))
    delta_implied_pct = (current_implied - open_implied) * 100.0

    # velocity = magnitude of the most recent step's implied-prob change.
    if len(ordered) >= 2:
        prev_implied = implied_prob(ordered[-2].odds_for(side))
        velocity = abs(current_implied - prev_implied) * 100.0
    else:
        velocity = 0.0

    band = cfg.movement_stable_band_pct
    if delta_implied_pct >= band:
        direction = "shortened"
    elif delta_implied_pct <= -band:
        direction = "drifted"
    else:
        direction = "stable"

    is_steam = (
        abs(delta_implied_pct) >= cfg.steam_threshold_pct
        or velocity >= cfg.steam_velocity_pct
    )

    # CLV proxy: how much better/worse the opening price was vs current for the
    # side we'd back. Treat the opening price as the entry -> same as delta.
    clv_proxy_pct = clv_proxy(first.odds_for(side), last.odds_for(side))

    return MarketMovement(
        side=side,
        open_implied=open_implied,
        current_implied=current_implied,
        delta_implied_pct=delta_implied_pct,
        direction=direction,
        is_steam=is_steam,
        velocity=velocity,
        clv_proxy_pct=clv_proxy_pct,
    )
