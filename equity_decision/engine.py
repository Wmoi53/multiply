"""
equity_decision — market-aware Buy/Hold/Sell decisions for US equities.

Same first-principles engine as the soccer Asian-Handicap `ah_decision`:
a fair probability, an edge over the MARKET's implied probability, a
growth-optimal (fractional-Kelly) size, and calibration scoring — just
with the market price / options-implied probability standing in for odds.

Decision is emitted as a TYPED, calibrated answer (a `choice` distribution
over BUY/HOLD/SELL + a conviction `score`), in the spirit of the
`typed-decisions` benchmark. Pure Python standard library.

NOTE: this does NOT predict stocks. It converts a probability you supply
(from your own model / options-implied view) into a sized, calibrated
decision. Garbage in -> garbage out. Nothing here is financial advice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

Action = Literal["BUY", "HOLD", "SELL"]


@dataclass
class EquityConfig:
    min_edge_pct: float = 3.0
    strong_edge_pct: float = 8.0
    momentum_confirm_discount_pct: float = 1.0
    momentum_adverse_bump_pct: float = 1.5
    high_vol_bump_pct: float = 1.0
    edge_floor_pct: float = 1.0
    kelly_multiplier: float = 0.25
    max_position_fraction: float = 0.10


def edge_pct(fair_p_up: float, market_p_up: float) -> float:
    """Your probability minus the market's implied probability, in pct points."""
    _check_prob(fair_p_up, "fair_p_up")
    _check_prob(market_p_up, "market_p_up")
    return (fair_p_up - market_p_up) * 100.0


def kelly_fraction(fair_p_up: float, market_p_up: float) -> float:
    """Growth-optimal bet fraction; market_p_up is the price (odds = 1/market_p_up). Negative -> 0."""
    _check_prob(fair_p_up, "fair_p_up")
    _check_prob(market_p_up, "market_p_up")
    if not 0.0 < market_p_up < 1.0:
        return 0.0
    odds = 1.0 / market_p_up
    b = odds - 1.0
    if b <= 0:
        return 0.0
    p, q = fair_p_up, 1.0 - fair_p_up
    f = (b * p - q) / b
    return max(0.0, f)


@dataclass
class MarketContext:
    """Recent conditions for the name. All optional."""
    momentum: float | None = None
    realized_vol: float | None = None
    high_vol_threshold: float = 0.40

    def adjust_required_edge(self, cfg: EquityConfig, side: Action, base: float) -> float:
        req = base
        if self.momentum is not None and side in ("BUY", "SELL"):
            trend_up = self.momentum > 0
            want_up = side == "BUY"
            if trend_up == want_up:
                req -= cfg.momentum_confirm_discount_pct
            else:
                req += cfg.momentum_adverse_bump_pct
        if self.realized_vol is not None and self.realized_vol >= self.high_vol_threshold:
            req += cfg.high_vol_bump_pct
        return max(cfg.edge_floor_pct, req)


@dataclass
class EquityDecision:
    action: Action
    edge_pct: float
    required_edge_pct: float
    position_fraction: float
    conviction: Literal["none", "low", "high"]
    probabilities: dict[str, float]
    rationale: str

    def __str__(self) -> str:
        return (f"{self.action} | edge {self.edge_pct:+.2f}pp vs required "
                f"{self.required_edge_pct:.2f}pp | size {self.position_fraction:.2%} "
                f"| conviction {self.conviction} | {self.rationale}")


def decide(cfg: EquityConfig, fair_p_up: float, market_p_up: float,
           context: MarketContext | None = None) -> EquityDecision:
    e = edge_pct(fair_p_up, market_p_up)
    ctx = context or MarketContext()
    side: Action = "BUY" if e > 0 else "SELL"
    req = ctx.adjust_required_edge(cfg, side, cfg.min_edge_pct)

    if abs(e) < req:
        probs = _softmax_choice(e, req)
        return EquityDecision(
            action="HOLD", edge_pct=e, required_edge_pct=req,
            position_fraction=0.0, conviction="none", probabilities=probs,
            rationale=f"|edge| {abs(e):.2f}pp below required {req:.2f}pp",
        )

    if side == "BUY":
        f = kelly_fraction(fair_p_up, market_p_up)
    else:
        f = kelly_fraction(1.0 - fair_p_up, 1.0 - market_p_up)
    size = min(cfg.kelly_multiplier * f, cfg.max_position_fraction)
    if size <= 0.0:
        # Edge clears the bar but Kelly sizing is zero (e.g. degenerate
        # market price of 0 or 1): a zero-size BUY/SELL is meaningless.
        return EquityDecision(
            action="HOLD", edge_pct=e, required_edge_pct=req,
            position_fraction=0.0, conviction="none",
            probabilities=_softmax_choice(e, req),
            rationale=(f"edge {e:+.2f}pp clears {req:.2f}pp but Kelly size is 0 "
                       f"(degenerate market price {market_p_up:g}); no trade"),
        )
    conviction = "high" if abs(e) >= cfg.strong_edge_pct - 1e-9 else "low"  # eps: float error (0.62-0.54)*100 = 7.999..99
    probs = _softmax_choice(e, req)
    return EquityDecision(
        action=side, edge_pct=e, required_edge_pct=req,
        position_fraction=size, conviction=conviction, probabilities=probs,
        rationale=(f"edge {e:+.2f}pp clears {req:.2f}pp; "
                   f"{cfg.kelly_multiplier:g}x Kelly -> {size:.2%}"),
    )


def brier_score(pred_probs: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean squared error of probabilistic forecasts. Lower is better."""
    if len(pred_probs) != len(outcomes) or not pred_probs:
        raise ValueError("pred_probs and outcomes must be non-empty, equal length")
    return sum((p - o) ** 2 for p, o in zip(pred_probs, outcomes)) / len(pred_probs)


def expected_calibration_error(pred_probs: Sequence[float],
                               outcomes: Sequence[int], bins: int = 10) -> float:
    """ECE: binned gap between confidence and accuracy. Lower is better."""
    if len(pred_probs) != len(outcomes) or not pred_probs:
        raise ValueError("pred_probs and outcomes must be non-empty, equal length")
    n = len(pred_probs)
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for p, o in zip(pred_probs, outcomes):
        idx = min(bins - 1, int(p * bins))
        buckets[idx].append((p, o))
    ece = 0.0
    for b in buckets:
        if not b:
            continue
        conf = sum(p for p, _ in b) / len(b)
        acc = sum(o for _, o in b) / len(b)
        ece += (len(b) / n) * abs(conf - acc)
    return ece


def _check_prob(x: float, name: str) -> None:
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {x}")


def _softmax_choice(e: float, req: float) -> dict[str, float]:
    """Heuristic BUY/HOLD/SELL distribution (softmax of edge / required edge).

    NOT a calibrated probability: it is a monotone squashing of how far the
    edge is from the required threshold, useful for ranking/presentation.
    Calibrate it against realized outcomes (see brier_score /
    expected_calibration_error) before treating it as a probability.
    """
    scale = max(req, 1e-6)
    logits = {"BUY": e / scale, "HOLD": 0.0, "SELL": -e / scale}
    m = max(logits.values())
    exp = {k: math.exp(v - m) for k, v in logits.items()}
    z = sum(exp.values())
    return {k: round(v / z, 4) for k, v in exp.items()}
