"""Market-aware Asian-Handicap decision engine.

Public API:
    Config              -- thresholds + defaults (+ optional YAML load)
    OddsSnapshot        -- one time-ordered odds observation
    MarketMovement      -- line-movement / steam / CLV signals for a side
    Decision            -- Bet/Pass result with sizing + rationale
    analyze_movement    -- build a MarketMovement from a snapshot series
    clv_proxy           -- closing-line-value proxy helper
    required_edge       -- minimum edge a side must clear (market-aware)
    decide              -- the top-level Bet/Pass + stake decision
    plus the market-math primitives (implied_prob, overround, ... , kelly_fraction)
"""

from __future__ import annotations

from .conditions import MarketMovement, OddsSnapshot, analyze_movement, clv_proxy
from .config import Config
from .engine import Decision, decide, required_edge
from .market import (
    devig_proportional,
    edge_pct,
    implied_prob,
    kelly_fraction,
    overround,
    overround_pct,
)

__all__ = [
    "Config",
    "OddsSnapshot",
    "MarketMovement",
    "Decision",
    "analyze_movement",
    "clv_proxy",
    "required_edge",
    "decide",
    "implied_prob",
    "overround",
    "overround_pct",
    "devig_proportional",
    "edge_pct",
    "kelly_fraction",
]

__version__ = "0.1.0"
