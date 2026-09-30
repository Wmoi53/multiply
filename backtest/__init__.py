"""Backtest harness for the market-aware Asian-Handicap decision engine.

This package turns the ``ah_decision`` engine's Bet/Pass + stake calls into
*measured edge*: it replays historical fixtures through ``ah_decision.decide``,
settles each resulting bet against the final score using proper Asian-Handicap
rules (whole / half / quarter lines, with half-win / push / half-loss), and
reports ROI, hit rate, CLV, calibration, and segment breakdowns.

Runtime is pure Python standard library (same as ``ah_decision``); ``pytest``
is only needed for the test suite.

Public API::

    from backtest import (
        BacktestFixture, load_fixtures_csv, load_fixtures_json,
        ah_result, settle_bet,
        BacktestResult, BetRecord, run_backtest,
        format_report,
    )
"""

from __future__ import annotations

from .data import (
    BacktestFixture,
    load_fixtures_csv,
    load_fixtures_json,
)
from .harness import BacktestResult, BetRecord, run_backtest
from .report import format_report
from .settlement import ah_result, settle_bet

__all__ = [
    "BacktestFixture",
    "load_fixtures_csv",
    "load_fixtures_json",
    "ah_result",
    "settle_bet",
    "BacktestResult",
    "BetRecord",
    "run_backtest",
    "format_report",
]

__version__ = "0.1.0"
