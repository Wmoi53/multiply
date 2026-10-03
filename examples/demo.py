"""End-to-end demo: seed a club/player, register an investor + a fan, submit
bids and watch auto-notifications fire.

Run with:  PYTHONPATH=src python examples/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from multiply.models import Club, Player, Subscriber  # noqa: E402
from multiply.service import ValuationService  # noqa: E402
from multiply.store import Store  # noqa: E402


def main() -> None:
    store = Store(":memory:")
    service = ValuationService(store)

    club = Club(id="ofc", name="Oakview FC", revenue_eur=90_000_000,
                net_debt_eur=20_000_000, league_tier=2)
    store.save_club(club)

    striker = Player(id="p1", name="A. Rossi", age=24, position="ST",
                      performance_score=82, contract_years_remaining=2.5, league_tier=2)
    store.save_player(striker, club_id="ofc")

    store.save_subscriber(Subscriber(id="inv1", name="Riverbend Capital", audience="investor",
                                      channel="console", contact="riverbend", watched_ids={"ofc", "p1"}))
    store.save_subscriber(Subscriber(id="fan1", name="Sam", audience="fan",
                                      channel="console", contact="sam"))

    print(f"Model value of {striker.name}: EUR {service.current_valuation('player', 'p1'):,.0f}")
    print(f"Model value of {club.name}: EUR {service.current_valuation('club', 'ofc'):,.0f}\n")

    print("--- Bid 1: rumoured, modest offer for the player ---")
    service.submit_bid("player", "p1", "Meridian United", 12_000_000, verified=False)

    print("--- Bid 2: verified club takeover offer ---")
    service.submit_bid("club", "ofc", "Northstar Partners", 260_000_000, verified=True)

    store.close()


if __name__ == "__main__":
    main()
