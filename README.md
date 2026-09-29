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
