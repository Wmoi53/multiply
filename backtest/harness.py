"""Backtest harness: replay fixtures through the engine and measure edge.

``run_backtest`` walks a list of :class:`~backtest.data.BacktestFixture`,
asks ``ah_decision.decide`` for a Bet/Pass call on each, settles the BETs with
:func:`~backtest.settlement.settle_bet`, and accumulates per-bet rows plus a
running bankroll. Two bankroll modes:

* ``'flat'``     -- every bet stakes ``stake_fraction * starting_bankroll``
  (level fractional staking; bankroll figure still compounds for reporting).
* ``'compound'`` -- every bet stakes ``stake_fraction * current_bankroll`` and
  the bankroll is updated by each settled bet's profit before the next.

:class:`BacktestResult.summary` reports counts, hit rate, ROI/yield, CLV,
edge-bucket calibration, and segment breakdowns (side, steam vs non-steam,
favorite vs underdog, deep vs shallow line).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ah_decision.config import Config
from ah_decision.engine import decide

from .data import BacktestFixture
from .settlement import settle_bet

__all__ = ["BetRecord", "BacktestResult", "run_backtest"]

_BANKROLL_MODES = ("flat", "compound")


@dataclass
class BetRecord:
    """One settled bet produced by the backtest."""

    label: str
    side: str
    odds: float
    line: float
    edge_pct: float
    stake_fraction: float
    stake_units: float          # actual units staked (stake_fraction * bankroll)
    result: float               # ah_result multiplier: 1/.5/0/-.5/-1
    profit_units: float         # actual profit in units on this bet
    bankroll_after: float       # running bankroll after settling this bet
    clv_proxy_pct: float
    is_steam: bool
    direction: str              # 'shortened' | 'drifted' | 'stable' | 'none'
    league: str | None = None
    bookmaker: str | None = None

    @property
    def is_favorite(self) -> bool:
        """Backed a favorite if the price taken is shorter than evens."""
        return self.odds < 2.0

    @property
    def is_deep_line(self) -> bool:
        """Deep handicap: |line| >= 1.5 (mirrors the engine's deep-line gate)."""
        return abs(self.line) >= 1.5

    @property
    def outcome_label(self) -> str:
        r = self.result
        if r == 1.0:
            return "win"
        if r == 0.5:
            return "half_win"
        if r == 0.0:
            return "push"
        if r == -0.5:
            return "half_loss"
        return "loss"


@dataclass
class BacktestResult:
    """Collected per-bet rows + fixture count, with a ``summary`` reducer."""

    n_fixtures: int
    bets: list[BetRecord] = field(default_factory=list)
    bankroll_mode: str = "flat"
    starting_bankroll: float = 1.0
    final_bankroll: float = 1.0

    # ---- aggregate helpers -------------------------------------------------
    def _bucket_yield(self, rows: list[BetRecord]) -> dict:
        staked = sum(r.stake_units for r in rows)
        profit = sum(r.profit_units for r in rows)
        return {
            "n": len(rows),
            "staked": staked,
            "profit": profit,
            "yield_pct": (profit / staked * 100.0) if staked > 0 else 0.0,
        }

    def summary(self) -> dict:
        """Reduce the per-bet rows into a metrics dict (see module docstring)."""
        bets = self.bets
        n_bets = len(bets)

        wins = sum(1 for b in bets if b.result == 1.0)
        half_wins = sum(1 for b in bets if b.result == 0.5)
        pushes = sum(1 for b in bets if b.result == 0.0)
        half_losses = sum(1 for b in bets if b.result == -0.5)
        losses = sum(1 for b in bets if b.result == -1.0)

        total_staked = sum(b.stake_units for b in bets)
        total_profit = sum(b.profit_units for b in bets)

        # Hit rate counts win-ish outcomes; half-win counts as half a hit,
        # pushes are excluded from the denominator (stake returned).
        decided = n_bets - pushes
        hit_units = wins + 0.5 * half_wins
        hit_rate = (hit_units / decided) if decided > 0 else 0.0

        avg_clv = (
            sum(b.clv_proxy_pct for b in bets) / n_bets if n_bets else 0.0
        )
        avg_edge = sum(b.edge_pct for b in bets) / n_bets if n_bets else 0.0

        roi = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0

        # Edge-bucket calibration: does higher predicted edge -> higher yield?
        edge_buckets: dict[str, dict] = {}
        bucket_defs = [
            ("<=1.5%", lambda e: e <= 1.5),
            ("1.5-3%", lambda e: 1.5 < e <= 3.0),
            ("3-5%", lambda e: 3.0 < e <= 5.0),
            (">5%", lambda e: e > 5.0),
        ]
        for name, pred in bucket_defs:
            rows = [b for b in bets if pred(b.edge_pct)]
            if rows:
                edge_buckets[name] = self._bucket_yield(rows)

        # Segment breakdowns.
        segments = {
            "by_side": {
                "home": self._bucket_yield([b for b in bets if b.side == "home"]),
                "away": self._bucket_yield([b for b in bets if b.side == "away"]),
            },
            "by_movement": {
                "steam": self._bucket_yield([b for b in bets if b.is_steam]),
                "non_steam": self._bucket_yield([b for b in bets if not b.is_steam]),
            },
            "by_price": {
                "favorite": self._bucket_yield([b for b in bets if b.is_favorite]),
                "underdog": self._bucket_yield([b for b in bets if not b.is_favorite]),
            },
            "by_line": {
                "deep": self._bucket_yield([b for b in bets if b.is_deep_line]),
                "shallow": self._bucket_yield([b for b in bets if not b.is_deep_line]),
            },
        }

        return {
            "n_fixtures": self.n_fixtures,
            "n_bets": n_bets,
            "bet_rate": (n_bets / self.n_fixtures) if self.n_fixtures else 0.0,
            "wins": wins,
            "half_wins": half_wins,
            "pushes": pushes,
            "half_losses": half_losses,
            "losses": losses,
            "hit_rate": hit_rate,
            "avg_edge_pct": avg_edge,
            "total_staked": total_staked,
            "total_profit": total_profit,
            "roi_pct": roi,
            "avg_clv_pct": avg_clv,
            "bankroll_mode": self.bankroll_mode,
            "starting_bankroll": self.starting_bankroll,
            "final_bankroll": self.final_bankroll,
            "growth_multiple": (
                self.final_bankroll / self.starting_bankroll
                if self.starting_bankroll
                else 0.0
            ),
            "edge_calibration": edge_buckets,
            "segments": segments,
        }


def run_backtest(
    cfg: Config,
    fixtures: list[BacktestFixture],
    bankroll_mode: str = "flat",
    starting_bankroll: float = 1.0,
) -> BacktestResult:
    """Replay ``fixtures`` through ``decide`` and settle the BETs.

    ``bankroll_mode`` is ``'flat'`` (stake off ``starting_bankroll`` each time)
    or ``'compound'`` (stake off the running bankroll). The running bankroll is
    tracked in both modes; only in ``'compound'`` does it feed back into stake
    sizing.
    """
    if bankroll_mode not in _BANKROLL_MODES:
        raise ValueError(
            f"bankroll_mode must be one of {_BANKROLL_MODES}, got {bankroll_mode!r}"
        )

    bankroll = starting_bankroll
    result = BacktestResult(
        n_fixtures=len(fixtures),
        bankroll_mode=bankroll_mode,
        starting_bankroll=starting_bankroll,
        final_bankroll=bankroll,
    )

    for fx in fixtures:
        snaps = fx.snapshots or None
        decision = decide(
            cfg,
            fx.fair_home,
            fx.fair_away,
            fx.home_odds,
            fx.away_odds,
            fx.line,
            snapshots=snaps,
        )
        if decision.action != "BET" or decision.side is None:
            continue

        stake_base = bankroll if bankroll_mode == "compound" else starting_bankroll
        stake_units = decision.stake_fraction * stake_base

        profit_per_unit = settle_bet(decision, fx)
        profit_units = profit_per_unit * stake_units
        bankroll += profit_units

        move = decision.movement
        result.bets.append(
            BetRecord(
                label=fx.label,
                side=decision.side,
                odds=fx.odds_for(decision.side),
                line=fx.line,
                edge_pct=decision.edge_pct,
                stake_fraction=decision.stake_fraction,
                stake_units=stake_units,
                result=_outcome_multiplier(decision, fx),
                profit_units=profit_units,
                bankroll_after=bankroll,
                clv_proxy_pct=decision.clv_proxy_pct,
                is_steam=bool(move.is_steam) if move else False,
                direction=move.direction if move else "none",
                league=fx.league,
                bookmaker=fx.bookmaker,
            )
        )

    result.final_bankroll = bankroll
    return result


def _outcome_multiplier(decision, fixture) -> float:
    """The canonical AH outcome multiplier (1/.5/0/-.5/-1) for reporting."""
    from .settlement import ah_result

    return ah_result(
        decision.side, fixture.line, fixture.home_goals, fixture.away_goals
    )
