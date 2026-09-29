"""Runnable worked example for the market-aware AH decision engine.

Run with:  python -m ah_decision.example

It walks through one fixture three ways -- no market data, a confirming
(shortening) move, and an adverse (drifting) move -- to show how recent market
conditions change the Bet/Pass call and the stake.
"""

from __future__ import annotations

from .config import Config
from .conditions import OddsSnapshot
from .engine import decide
from .market import devig_proportional, overround_pct


def main() -> None:
    cfg = Config()

    # A modelled fixture: home is the AH favorite at -0.5 line.
    home_odds, away_odds = 1.90, 2.05
    line = -0.5

    # Our fair (model) probabilities -- slightly favor home over the market.
    fair_home, fair_away = 0.56, 0.44

    fair_market = devig_proportional([home_odds, away_odds])
    print("=== Market-Aware Asian-Handicap Decision Engine ===")
    print(f"Line (home): {line:+.2f}")
    print(f"Odds: home {home_odds}  away {away_odds}")
    print(f"Book overround: {overround_pct(home_odds, away_odds):.2f}%")
    print(f"De-vigged market probs: home {fair_market[0]:.3f}  away {fair_market[1]:.3f}")
    print(f"Our fair probs:         home {fair_home:.3f}  away {fair_away:.3f}")
    print()

    # 1) No recent-market data (static snapshot only).
    d_static = decide(cfg, fair_home, fair_away, home_odds, away_odds, line)
    print("[1] No market movement supplied:")
    print(d_static)
    print()

    # 2) Market confirming our home pick: price shortens 1.90 -> 1.78 (steam).
    confirming = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.84, away_odds=2.00),
        OddsSnapshot(ts=120, home_odds=1.78, away_odds=1.95),
    ]
    d_confirm = decide(
        cfg, fair_home, fair_away, home_odds, away_odds, line, snapshots=confirming
    )
    print("[2] Market shortening on home (confirming, steam):")
    print(d_confirm)
    if d_confirm.movement:
        m = d_confirm.movement
        print(
            f"    movement: {m.direction}, delta {m.delta_implied_pct:+.2f}pp, "
            f"steam={m.is_steam}, CLV proxy {m.clv_proxy_pct:+.2f}pp"
        )
    print()

    # 3) Market drifting against our home pick: price drifts 1.90 -> 2.02.
    adverse = [
        OddsSnapshot(ts=0, home_odds=1.90, away_odds=2.05),
        OddsSnapshot(ts=60, home_odds=1.96, away_odds=1.98),
        OddsSnapshot(ts=120, home_odds=2.02, away_odds=1.92),
    ]
    d_adverse = decide(
        cfg, fair_home, fair_away, home_odds, away_odds, line, snapshots=adverse
    )
    print("[3] Market drifting on home (adverse):")
    print(d_adverse)
    if d_adverse.movement:
        m = d_adverse.movement
        print(
            f"    movement: {m.direction}, delta {m.delta_implied_pct:+.2f}pp, "
            f"steam={m.is_steam}, CLV proxy {m.clv_proxy_pct:+.2f}pp"
        )


if __name__ == "__main__":
    main()
