"""First-principles market math for Asian-Handicap / value betting.

All functions here are standard, non-proprietary bookmaking arithmetic:
converting decimal odds to implied probabilities, measuring the book's
overround (vig), removing the vig, and computing betting edge and Kelly
stakes. Pure Python standard library only.
"""

from __future__ import annotations

__all__ = [
    "implied_prob",
    "overround",
    "overround_pct",
    "devig_proportional",
    "edge_pct",
    "kelly_fraction",
]


def _validate_odds(decimal_odds: float) -> None:
    """Decimal odds must be strictly greater than 1.0 (a real payout)."""
    if not isinstance(decimal_odds, (int, float)):
        raise ValueError(f"decimal odds must be numeric, got {decimal_odds!r}")
    if decimal_odds <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {decimal_odds!r}")


def _validate_prob(prob: float) -> None:
    """Probabilities must live in [0, 1]."""
    if not isinstance(prob, (int, float)):
        raise ValueError(f"probability must be numeric, got {prob!r}")
    if prob < 0.0 or prob > 1.0:
        raise ValueError(f"probability must be in [0, 1], got {prob!r}")


def implied_prob(decimal_odds: float) -> float:
    """Bookmaker-implied probability of an outcome = 1 / decimal_odds."""
    _validate_odds(decimal_odds)
    return 1.0 / decimal_odds


def overround(*decimal_odds: float) -> float:
    """Sum of implied probabilities across a market.

    A fair (vig-free) two-way market sums to 1.0; anything above 1.0 is the
    book's margin (overround / vig).
    """
    if not decimal_odds:
        raise ValueError("overround requires at least one odds value")
    return sum(implied_prob(o) for o in decimal_odds)


def overround_pct(*decimal_odds: float) -> float:
    """Overround expressed as a percentage margin, e.g. 1.05 -> 5.0."""
    return (overround(*decimal_odds) - 1.0) * 100.0


def devig_proportional(odds_list: list[float]) -> list[float]:
    """Proportional (a.k.a. normalized/multiplicative) de-vig.

    Divide each implied probability by the total overround so the resulting
    fair probabilities sum to exactly 1.0. This is the simplest, most common
    de-vig and is used as the default here.
    """
    if not odds_list:
        raise ValueError("devig_proportional requires at least one odds value")
    implied = [implied_prob(o) for o in odds_list]
    total = sum(implied)
    if total <= 0.0:  # pragma: no cover - implied probs are always > 0 for odds > 1
        raise ValueError("total implied probability must be positive")
    return [p / total for p in implied]


def edge_pct(fair_prob: float, decimal_odds: float) -> float:
    """Betting edge in percentage points: (fair_prob - implied_prob) * 100.

    Positive means the fair model rates the outcome more likely than the
    price implies (a value bet). This is an expected-value proxy.
    """
    _validate_prob(fair_prob)
    _validate_odds(decimal_odds)
    return (fair_prob - implied_prob(decimal_odds)) * 100.0


def kelly_fraction(fair_prob: float, decimal_odds: float) -> float:
    """Full-Kelly optimal stake fraction of bankroll.

    f* = (b*p - q) / b, where b = decimal_odds - 1, p = fair_prob, q = 1 - p.
    Negative results (no edge) are clamped to 0.0 (do not bet).
    """
    _validate_prob(fair_prob)
    _validate_odds(decimal_odds)
    b = decimal_odds - 1.0
    p = fair_prob
    q = 1.0 - p
    f = (b * p - q) / b
    return f if f > 0.0 else 0.0
