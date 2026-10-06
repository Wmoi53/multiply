"""equity_decision: market-aware Buy/Hold/Sell decisions for US equities."""

from .engine import (
    EquityConfig,
    EquityDecision,
    MarketContext,
    brier_score,
    decide,
    edge_pct,
    expected_calibration_error,
    kelly_fraction,
)

__all__ = [
    "EquityConfig", "MarketContext", "EquityDecision", "decide", "edge_pct",
    "kelly_fraction", "brier_score", "expected_calibration_error",
]
