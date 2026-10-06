"""Market-aware decision engine + fractional-Kelly stake sizing.

``required_edge`` computes the minimum edge a side must clear to be bettable,
starting from a baseline and escalating for risky prices/lines -- then, the new
part, *adjusting for recent market conditions*: it lowers the bar when the
market is confirming our pick (shortening, especially on steam) and raises it
when the market is moving against us (drifting). ``decide`` gates on overround,
picks the best bettable side, and sizes the stake with fractional Kelly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .conditions import MarketMovement, OddsSnapshot, analyze_movement
from .config import Config
from .market import edge_pct, kelly_fraction, overround_pct

__all__ = ["Decision", "required_edge", "decide"]


@dataclass
class Decision:
    """Outcome of the engine for a single match."""

    action: str                          # 'BET' | 'PASS'
    side: str | None                     # 'home' | 'away' | None
    edge_pct: float                      # edge of the chosen/best side
    required_edge_pct: float             # threshold that side had to clear
    stake_fraction: float                # fractional-Kelly stake (fraction of bankroll)
    clv_proxy_pct: float                 # chosen side's CLV proxy (0.0 if no movement)
    movement: MarketMovement | None      # chosen side's movement analysis, if any
    rationale: str                       # human-readable list of rules that fired

    def __str__(self) -> str:
        if self.action == "BET":
            head = (
                f"BET {self.side}: edge {self.edge_pct:.2f}% "
                f">= required {self.required_edge_pct:.2f}%, "
                f"stake {self.stake_fraction * 100:.2f}% of bankroll"
            )
        else:
            head = "PASS"
        return f"{head}\n  {self.rationale}"


def _required_edge_with_reasons(
    cfg: Config,
    decimal_odds: float,
    line: float,
    movement: MarketMovement | None = None,
) -> tuple[float, list[str]]:
    """Core of ``required_edge`` that also returns the list of rules that fired."""
    reasons: list[str] = []
    threshold = cfg.min_abs_edge_pct
    reasons.append(f"base {threshold:.2f}%")

    # Extreme prices are noisy / low-value: demand more edge.
    if decimal_odds < cfg.extreme_low_odds or decimal_odds > cfg.extreme_high_odds:
        new = max(threshold, cfg.extreme_edge_pct)
        if new != threshold:
            reasons.append(f"extreme price -> {new:.2f}%")
        threshold = new

    # Short favorites / long dogs carry skew risk: demand more edge.
    if decimal_odds <= cfg.short_fav_odds or decimal_odds >= cfg.long_dog_odds:
        new = max(threshold, cfg.price_skew_edge_pct)
        if new != threshold:
            reasons.append(f"price skew -> {new:.2f}%")
        threshold = new

    # Deep handicap lines are harder to model: demand more edge.
    if abs(line) >= cfg.deep_line_threshold:
        new = max(threshold, cfg.deep_line_edge_pct)
        if new != threshold:
            reasons.append(f"deep line -> {new:.2f}%")
        threshold = new

    # --- recent-market-condition adjustment (the new part) ---
    if movement is not None:
        if movement.direction == "shortened":
            discount = cfg.movement_confirm_discount_pct
            if movement.is_steam:
                discount += cfg.steam_confirm_extra_pct
            threshold -= discount
            reasons.append(
                f"market confirming ({'steam ' if movement.is_steam else ''}"
                f"shortened) -> -{discount:.2f}%"
            )
        elif movement.direction == "drifted":
            bump = cfg.movement_adverse_bump_pct
            if movement.is_steam:
                bump += cfg.steam_adverse_extra_pct
            threshold += bump
            reasons.append(
                f"market against ({'steam ' if movement.is_steam else ''}"
                f"drifted) -> +{bump:.2f}%"
            )

    # Never let the required edge fall below the hard floor.
    if threshold < cfg.edge_floor_pct:
        threshold = cfg.edge_floor_pct
        reasons.append(f"floored at {cfg.edge_floor_pct:.2f}%")

    return threshold, reasons


def required_edge(
    cfg: Config,
    decimal_odds: float,
    line: float,
    movement: MarketMovement | None = None,
) -> float:
    """Minimum edge (percentage points) a side must clear to be bettable.

    Each rule raises the bar for a reason; the market-condition adjustment can
    lower or raise it. The result is clamped to never fall below the hard floor.
    """
    threshold, _ = _required_edge_with_reasons(cfg, decimal_odds, line, movement)
    return threshold


def _price_skew(decimal_odds: float) -> float:
    """Distance of a price from evens (2.0). Larger = more skewed."""
    return abs(decimal_odds - 2.0)


def decide(
    cfg: Config,
    fair_home: float,
    fair_away: float,
    home_odds: float,
    away_odds: float,
    line: float,
    snapshots: list[OddsSnapshot] | None = None,
) -> Decision:
    """Market-aware Bet/Pass decision for a two-way Asian-Handicap market."""

    # 1) Overround gate: skip books that are too juicy to beat.
    book_overround = overround_pct(home_odds, away_odds)
    if book_overround > cfg.max_overround_pct:
        return Decision(
            action="PASS",
            side=None,
            edge_pct=0.0,
            required_edge_pct=0.0,
            stake_fraction=0.0,
            clv_proxy_pct=0.0,
            movement=None,
            rationale=(
                f"PASS: overround {book_overround:.2f}% exceeds max "
                f"{cfg.max_overround_pct:.2f}% (book too juicy)."
            ),
        )

    # 2) Edge per side, using the raw price (edge = fair - implied).
    home_edge = edge_pct(fair_home, home_odds)
    away_edge = edge_pct(fair_away, away_odds)

    # 3) Movement analysis per side, if a snapshot series was supplied.
    home_move: MarketMovement | None = None
    away_move: MarketMovement | None = None
    if snapshots:
        home_move = analyze_movement(snapshots, "home", cfg)
        away_move = analyze_movement(snapshots, "away", cfg)

    sides = [
        ("home", home_edge, home_odds, fair_home, home_move),
        ("away", away_edge, away_odds, fair_away, away_move),
    ]

    # 4) Determine which sides are bettable and record each threshold/reasoning.
    bettable = []
    req_by_side: dict[str, float] = {}
    reasons_by_side: dict[str, list[str]] = {}
    for name, edge, odds, _fair, move in sides:
        req, reasons = _required_edge_with_reasons(cfg, odds, line, move)
        req_by_side[name] = req
        reasons_by_side[name] = reasons
        if edge > 0.0 and edge >= req:
            bettable.append((name, edge, odds, _fair, move))

    # 5) No bettable side -> PASS with the best side's numbers for context.
    if not bettable:
        best_name, best_edge, best_odds, _bf, best_move = max(
            sides, key=lambda s: s[1]
        )
        return Decision(
            action="PASS",
            side=None,
            edge_pct=best_edge,
            required_edge_pct=req_by_side[best_name],
            stake_fraction=0.0,
            clv_proxy_pct=best_move.clv_proxy_pct if best_move else 0.0,
            movement=best_move,
            rationale=(
                f"PASS: best side {best_name} edge {best_edge:.2f}% did not clear "
                f"required {req_by_side[best_name]:.2f}% "
                f"[{'; '.join(reasons_by_side[best_name])}]."
            ),
        )

    # 6) Choose among bettable: larger edge wins; near-ties favor the price
    #    further from evens (more skewed = more information in the price).
    if len(bettable) == 2:
        a, b = bettable
        if abs(a[1] - b[1]) <= cfg.tie_breaker_delta_pct:
            chosen = a if _price_skew(a[2]) >= _price_skew(b[2]) else b
            tie_note = (
                f" (tie-breaker: edges within {cfg.tie_breaker_delta_pct:.2f}%, "
                f"chose price further from 2.0)"
            )
        else:
            chosen = a if a[1] >= b[1] else b
            tie_note = ""
    else:
        chosen = bettable[0]
        tie_note = ""

    name, edge, odds, fair, move = chosen

    # 7) Fractional-Kelly stake sizing, clamped to the configured cap.
    raw_kelly = kelly_fraction(fair, odds)
    stake = cfg.kelly_multiplier * raw_kelly
    if stake > cfg.max_stake_fraction:
        stake = cfg.max_stake_fraction
        clamp_note = f", stake clamped to max {cfg.max_stake_fraction * 100:.2f}%"
    else:
        clamp_note = ""
    if stake < 0.0:
        stake = 0.0

    rationale = (
        f"BET {name}: edge {edge:.2f}% >= required {req_by_side[name]:.2f}% "
        f"[{'; '.join(reasons_by_side[name])}]{tie_note}. "
        f"Stake = {cfg.kelly_multiplier:.2f} x Kelly {raw_kelly * 100:.2f}% "
        f"= {stake * 100:.2f}% of bankroll{clamp_note}."
    )

    return Decision(
        action="BET",
        side=name,
        edge_pct=edge,
        required_edge_pct=req_by_side[name],
        stake_fraction=stake,
        clv_proxy_pct=move.clv_proxy_pct if move else 0.0,
        movement=move,
        rationale=rationale,
    )
