"""Console report + CLI for the backtest harness.

``format_report`` renders a :class:`~backtest.harness.BacktestResult` into a
clean, dependency-free text report. The module also exposes a small CLI::

    python -m backtest run <fixtures.csv|.json> [--config path.yaml]
                              [--mode flat|compound] [--bankroll 1.0]

It loads the fixtures, runs the backtest, and prints the report.
"""

from __future__ import annotations

import argparse
import sys

from ah_decision.config import Config

from .data import load_fixtures_csv, load_fixtures_json
from .harness import BacktestResult, run_backtest

__all__ = ["format_report", "main"]


def _fmt_bucket(b: dict) -> str:
    return (
        f"n={b['n']:<3d} staked={b['staked']:.3f} "
        f"profit={b['profit']:+.3f} yield={b['yield_pct']:+.2f}%"
    )


def format_report(result: BacktestResult) -> str:
    """Render a readable console report for a backtest result."""
    s = result.summary()
    lines: list[str] = []
    add = lines.append

    add("=" * 66)
    add("  Asian-Handicap Backtest Report")
    add("=" * 66)
    add(f"  Fixtures evaluated : {s['n_fixtures']}")
    add(f"  Bets placed        : {s['n_bets']}  (bet rate {s['bet_rate'] * 100:.1f}%)")
    add(
        f"  Outcomes           : {s['wins']}W  {s['half_wins']}HW  "
        f"{s['pushes']}P  {s['half_losses']}HL  {s['losses']}L"
    )
    add(f"  Hit rate           : {s['hit_rate'] * 100:.2f}%  (pushes excluded)")
    add(f"  Avg predicted edge : {s['avg_edge_pct']:+.2f}%")
    add("")
    add(f"  Total staked       : {s['total_staked']:.4f} units")
    add(f"  Total profit       : {s['total_profit']:+.4f} units")
    add(f"  ROI / yield        : {s['roi_pct']:+.2f}%")
    add(f"  Avg CLV proxy      : {s['avg_clv_pct']:+.2f}pp")
    add("")
    add(
        f"  Bankroll ({s['bankroll_mode']}): "
        f"{s['starting_bankroll']:.4f} -> {s['final_bankroll']:.4f}  "
        f"(x{s['growth_multiple']:.4f})"
    )

    add("")
    add("-" * 66)
    add("  Edge-bucket calibration (predicted edge -> realized yield)")
    add("-" * 66)
    if s["edge_calibration"]:
        for name, b in s["edge_calibration"].items():
            add(f"  {name:<8s} {_fmt_bucket(b)}")
    else:
        add("  (no bets)")

    add("")
    add("-" * 66)
    add("  Segment breakdowns")
    add("-" * 66)
    for seg_name, seg in s["segments"].items():
        add(f"  {seg_name}:")
        for key, b in seg.items():
            add(f"    {key:<10s} {_fmt_bucket(b)}")

    add("=" * 66)
    return "\n".join(lines)


def _load_fixtures(path: str):
    if path.lower().endswith(".json"):
        return load_fixtures_json(path)
    return load_fixtures_csv(path)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m backtest",
        description="Backtest the market-aware Asian-Handicap decision engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run a backtest over a fixtures file")
    run_p.add_argument("fixtures", help="path to fixtures .csv or .json")
    run_p.add_argument(
        "--config",
        default=None,
        help="path to a Config YAML (default: engine defaults)",
    )
    run_p.add_argument(
        "--mode",
        choices=("flat", "compound"),
        default="flat",
        help="bankroll mode (default: flat)",
    )
    run_p.add_argument(
        "--bankroll",
        type=float,
        default=1.0,
        help="starting bankroll (default: 1.0)",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        cfg = Config.from_yaml(args.config) if args.config else Config()
        fixtures = _load_fixtures(args.fixtures)
        result = run_backtest(
            cfg,
            fixtures,
            bankroll_mode=args.mode,
            starting_bankroll=args.bankroll,
        )
        print(format_report(result))
        return 0

    parser.error(f"unknown command {args.command!r}")  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
