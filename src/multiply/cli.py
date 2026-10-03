"""Command-line interface for the valuation/bidding notifier.

Examples
--------
    python -m multiply.cli add-club --id ofc --name "Oakview FC" \\
        --revenue 90000000 --net-debt 20000000 --tier 2

    python -m multiply.cli add-player --id p1 --name "A. Rossi" --age 24 \\
        --position ST --performance 78 --contract-years 2.5 --tier 2 --club ofc

    python -m multiply.cli add-subscriber --id inv1 --name "Riverbend Capital" \\
        --audience investor --channel console --contact riverbend --watch ofc

    python -m multiply.cli bid --target-type club --target-id ofc \\
        --bidder "Northstar Partners" --amount 250000000 --verified

    python -m multiply.cli value --target-type club --target-id ofc
"""

from __future__ import annotations

import argparse
import sys

from .models import Club, Player, Subscriber
from .service import ValuationService
from .store import Store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="multiply", description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="multiply.db", help="sqlite db path (default: multiply.db)")
    sub = parser.add_subparsers(dest="command", required=True)

    club = sub.add_parser("add-club", help="create or update a club")
    club.add_argument("--id", required=True)
    club.add_argument("--name", required=True)
    club.add_argument("--revenue", type=float, required=True, help="annual revenue in EUR")
    club.add_argument("--net-debt", type=float, required=True, help="net debt in EUR")
    club.add_argument("--tier", type=int, required=True, choices=range(1, 6))

    player = sub.add_parser("add-player", help="create or update a player")
    player.add_argument("--id", required=True)
    player.add_argument("--name", required=True)
    player.add_argument("--age", type=int, required=True)
    player.add_argument("--position", required=True)
    player.add_argument("--performance", type=float, required=True, help="0-100 performance score")
    player.add_argument("--contract-years", type=float, required=True)
    player.add_argument("--tier", type=int, required=True, choices=range(1, 6))
    player.add_argument("--club", help="club id to attach this player to")

    subscriber = sub.add_parser("add-subscriber", help="register an investor or fan")
    subscriber.add_argument("--id", required=True)
    subscriber.add_argument("--name", required=True)
    subscriber.add_argument("--audience", required=True, choices=["investor", "fan"])
    subscriber.add_argument("--channel", required=True, choices=["console", "email", "webhook"])
    subscriber.add_argument("--contact", required=True, help="email address, webhook URL, or handle")
    subscriber.add_argument("--watch", nargs="*", default=None,
                             help="target ids to watch; omit to watch everything")

    bid = sub.add_parser("bid", help="submit a bid and auto-notify watchers if notify-worthy")
    bid.add_argument("--target-type", required=True, choices=["player", "club"])
    bid.add_argument("--target-id", required=True)
    bid.add_argument("--bidder", required=True)
    bid.add_argument("--amount", type=float, required=True, help="bid amount in EUR")
    bid.add_argument("--verified", action="store_true")

    value = sub.add_parser("value", help="print the current model valuation")
    value.add_argument("--target-type", required=True, choices=["player", "club"])
    value.add_argument("--target-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    store = Store(args.db)
    service = ValuationService(store)

    try:
        if args.command == "add-club":
            store.save_club(Club(id=args.id, name=args.name, revenue_eur=args.revenue,
                                  net_debt_eur=args.net_debt, league_tier=args.tier))
            print(f"saved club {args.id}")

        elif args.command == "add-player":
            store.save_player(
                Player(id=args.id, name=args.name, age=args.age, position=args.position,
                       performance_score=args.performance,
                       contract_years_remaining=args.contract_years, league_tier=args.tier),
                club_id=args.club,
            )
            print(f"saved player {args.id}")

        elif args.command == "add-subscriber":
            watched = set(args.watch) if args.watch else None
            store.save_subscriber(Subscriber(id=args.id, name=args.name, audience=args.audience,
                                              channel=args.channel, contact=args.contact,
                                              watched_ids=watched))
            print(f"saved subscriber {args.id}")

        elif args.command == "bid":
            bid, notified = service.submit_bid(args.target_type, args.target_id, args.bidder,
                                                args.amount, verified=args.verified)
            print(f"bid {bid.id} recorded; notified={notified}")

        elif args.command == "value":
            print(f"{service.current_valuation(args.target_type, args.target_id):,.0f}")

    finally:
        store.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
