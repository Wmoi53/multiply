# multiply
agent multi tasking for a single project in 60days

## `ah_decision` — market-aware Asian-Handicap decision engine

A dependency-light decision engine for the soccer Asian-Handicap / value-betting
pipeline. It turns model "fair" probabilities plus bookmaker odds into a
**Bet/Pass** call with **fractional-Kelly** stake sizing.

The improvement over a static odds snapshot: the Bet/Pass decision factors in
**recent market conditions** — line movement, steam (sharp confirmed moves), and
a closing-line-value (CLV) proxy — not just a single frozen price. When the
market is confirming our pick (the price is shortening, especially on steam) the
engine *lowers* the required edge; when the market is drifting against us it
*raises* the bar.

The engine runtime is **pure Python standard library** (no numpy/scipy/pyyaml).
`pytest` is only a dev/test dependency. Targets Python 3.10+.

### What it does

- `market.py` — first-principles market math: implied probability, overround /
  vig, proportional de-vig, edge, and full-Kelly fraction (with input validation).
- `conditions.py` — analyzes a time-ordered series of `OddsSnapshot`s into a
  `MarketMovement` (direction shortened/drifted/stable, `is_steam`, velocity, and
  a CLV proxy).
- `engine.py` — `required_edge()` (baseline edge escalated for extreme prices,
  skewed prices, and deep lines, then adjusted by market conditions) and
  `decide()` (overround gate, per-side edge, side selection with tie-breaker, and
  fractional-Kelly stake sizing capped at a max fraction). Returns a `Decision`
  with a human-readable rationale.
- `config.py` — a `Config` dataclass holding every threshold with sensible
  defaults, plus `Config.from_yaml()` (lazy PyYAML import with a built-in flat
  parser fallback so defaults work with zero dependencies).

### Public API

```python
from ah_decision import (
    Config, OddsSnapshot, MarketMovement, Decision,
    analyze_movement, clv_proxy, required_edge, decide,
    implied_prob, overround, overround_pct, devig_proportional,
    edge_pct, kelly_fraction,
)
```

### Run the worked example

```bash
python -m ah_decision.example
```

It evaluates one fixture three ways — no market data, a confirming (shortening)
move, and an adverse (drifting) move — showing how the required edge, and thus
the decision, respond to recent market conditions.

### Run the tests

```bash
pip install -r requirements.txt   # installs pytest (dev only)
python -m pytest -q
```

### Configuration

Defaults live in `ah_decision/config.py`. `config/pipeline_config.yaml` mirrors
them with per-threshold comments and can be loaded via
`Config.from_yaml("config/pipeline_config.yaml")`.

## Backtesting

The `backtest/` package turns the decision logic into **measured edge**: it
replays historical fixtures through `ah_decision.decide`, settles each resulting
bet against the final score using proper Asian-Handicap rules, and reports ROI,
hit rate, CLV, calibration, and segment breakdowns. Runtime is pure Python
standard library (same as the engine); `pytest` is only needed for the tests.

### Fixture schema

Each fixture carries the engine inputs plus the settled final score (so
Asian-Handicap settlement is unambiguous). CSV columns:

| column | type | meaning |
| --- | --- | --- |
| `label` | str | fixture identifier |
| `home_odds` / `away_odds` | float | decimal odds for each side of the AH market |
| `fair_home` / `fair_away` | float | model fair probabilities (0..1) |
| `line` | float | **home-side** handicap (e.g. `-0.5`, `+0.25`, `-1.0`) |
| `home_goals` / `away_goals` | int | final score |
| `league` / `kickoff` / `bookmaker` | str | optional metadata for segment breakdowns |
| `snapshots` | str | optional odds series `"ts:home:away|ts:home:away|..."` |

JSON fixtures (`load_fixtures_json`) use the same field names, with `snapshots`
as a list of `{"ts", "home_odds", "away_odds"}` objects. The sign convention
matches the engine: `line` is the home handicap and the away handicap is its
negation.

### Settlement

`settlement.ah_result(side, line, home_goals, away_goals)` returns a canonical
outcome multiplier — `+1.0` full win, `+0.5` half win, `0.0` push, `-0.5` half
loss, `-1.0` full loss — handling **whole** lines (win/push/loss), **half**
lines (win/loss only), and **quarter** lines (stake split across the two
adjacent lines, enabling half-win/half-loss). `settlement.settle_bet(decision,
fixture)` converts that to profit for a 1-unit stake at the bet side's price:
`(odds-1)` on a full win, `(odds-1)/2` on a half win, `0` on a push, `-0.5` on a
half loss, `-1` on a full loss. PASS decisions settle to `0.0`.

### Metrics

`harness.run_backtest(cfg, fixtures, bankroll_mode, starting_bankroll)` loops the
fixtures, calls `decide`, stakes `stake_fraction × bankroll` on each BET, and
returns a `BacktestResult`. `bankroll_mode='flat'` stakes off the starting
bankroll each time; `'compound'` stakes off the running bankroll and lets it
feed back into sizing. `BacktestResult.summary()` reports fixture/bet counts,
bet rate, win/half/push/loss counts, hit rate (pushes excluded), total staked,
total profit, ROI/yield, average CLV proxy, final bankroll and growth multiple,
plus edge-bucket **calibration** (predicted edge → realized yield) and **segment
breakdowns** by side, steam vs non-steam movement, favorite vs underdog
(price < 2.0), and deep vs shallow line (|line| ≥ 1.5).

### Run the backtest CLI

```bash
python -m backtest run examples/sample_fixtures.csv
python -m backtest run examples/sample_fixtures.csv --mode compound
python -m backtest run fixtures.json --config config/pipeline_config.yaml --bankroll 100
```

`examples/sample_fixtures.csv` ships a dozen illustrative fixtures (favorites,
underdogs, whole/half/quarter lines, and a couple with steam movement) so the
CLI runs out of the box.
