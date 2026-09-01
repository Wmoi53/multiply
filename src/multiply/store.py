"""SQLite-backed persistence for players, clubs, bids and subscribers."""

from __future__ import annotations

import json
import sqlite3

from .models import Bid, Club, Player, Subscriber

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    position TEXT NOT NULL,
    performance_score REAL NOT NULL,
    contract_years_remaining REAL NOT NULL,
    league_tier INTEGER NOT NULL,
    club_id TEXT
);

CREATE TABLE IF NOT EXISTS clubs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    revenue_eur REAL NOT NULL,
    net_debt_eur REAL NOT NULL,
    league_tier INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bids (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    bidder TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    verified INTEGER NOT NULL,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS subscribers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    audience TEXT NOT NULL,
    channel TEXT NOT NULL,
    contact TEXT NOT NULL,
    watched_ids TEXT
);
"""


class Store:
    """Thin repository wrapping a single sqlite3 connection.

    Pass ``:memory:`` for tests/demos; a file path for persistence across runs.
    """

    def __init__(self, path: str = "multiply.db") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- clubs ---------------------------------------------------------
    def save_club(self, club: Club) -> None:
        self._conn.execute(
            """INSERT INTO clubs (id, name, revenue_eur, net_debt_eur, league_tier)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name, revenue_eur=excluded.revenue_eur,
                   net_debt_eur=excluded.net_debt_eur, league_tier=excluded.league_tier""",
            (club.id, club.name, club.revenue_eur, club.net_debt_eur, club.league_tier),
        )
        for player in club.squad:
            self.save_player(player, club_id=club.id)
        self._conn.commit()

    def get_club(self, club_id: str) -> Club | None:
        row = self._conn.execute("SELECT * FROM clubs WHERE id = ?", (club_id,)).fetchone()
        if row is None:
            return None
        squad = [self._row_to_player(r) for r in self._conn.execute(
            "SELECT * FROM players WHERE club_id = ?", (club_id,)
        )]
        return Club(
            id=row["id"], name=row["name"], revenue_eur=row["revenue_eur"],
            net_debt_eur=row["net_debt_eur"], league_tier=row["league_tier"], squad=squad,
        )

    # -- players ---------------------------------------------------------
    def save_player(self, player: Player, club_id: str | None = None) -> None:
        self._conn.execute(
            """INSERT INTO players
                   (id, name, age, position, performance_score, contract_years_remaining, league_tier, club_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name, age=excluded.age, position=excluded.position,
                   performance_score=excluded.performance_score,
                   contract_years_remaining=excluded.contract_years_remaining,
                   league_tier=excluded.league_tier,
                   club_id=COALESCE(excluded.club_id, players.club_id)""",
            (
                player.id, player.name, player.age, player.position,
                player.performance_score, player.contract_years_remaining,
                player.league_tier, club_id,
            ),
        )
        self._conn.commit()

    def get_player(self, player_id: str) -> Player | None:
        row = self._conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return self._row_to_player(row) if row else None

    @staticmethod
    def _row_to_player(row: sqlite3.Row) -> Player:
        return Player(
            id=row["id"], name=row["name"], age=row["age"], position=row["position"],
            performance_score=row["performance_score"],
            contract_years_remaining=row["contract_years_remaining"],
            league_tier=row["league_tier"],
        )

    # -- bids ---------------------------------------------------------
    def save_bid(self, bid: Bid) -> None:
        self._conn.execute(
            """INSERT INTO bids (id, target_type, target_id, bidder, amount_eur, verified, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (bid.id, bid.target_type, bid.target_id, bid.bidder, bid.amount_eur,
             int(bid.verified), bid.timestamp),
        )
        self._conn.commit()

    def get_highest_bid(
        self, target_type: str, target_id: str, exclude_id: str | None = None
    ) -> Bid | None:
        rows = self._conn.execute(
            """SELECT * FROM bids WHERE target_type = ? AND target_id = ?
               ORDER BY amount_eur DESC""",
            (target_type, target_id),
        ).fetchall()
        for row in rows:
            if exclude_id is not None and row["id"] == exclude_id:
                continue
            return self._row_to_bid(row)
        return None

    def list_bids(self, target_type: str, target_id: str) -> list[Bid]:
        rows = self._conn.execute(
            """SELECT * FROM bids WHERE target_type = ? AND target_id = ?
               ORDER BY timestamp ASC""",
            (target_type, target_id),
        ).fetchall()
        return [self._row_to_bid(r) for r in rows]

    @staticmethod
    def _row_to_bid(row: sqlite3.Row) -> Bid:
        return Bid(
            id=row["id"], target_type=row["target_type"], target_id=row["target_id"],
            bidder=row["bidder"], amount_eur=row["amount_eur"],
            verified=bool(row["verified"]), timestamp=row["timestamp"],
        )

    # -- subscribers ---------------------------------------------------------
    def save_subscriber(self, subscriber: Subscriber) -> None:
        watched = json.dumps(sorted(subscriber.watched_ids)) if subscriber.watched_ids else None
        self._conn.execute(
            """INSERT INTO subscribers (id, name, audience, channel, contact, watched_ids)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name, audience=excluded.audience, channel=excluded.channel,
                   contact=excluded.contact, watched_ids=excluded.watched_ids""",
            (subscriber.id, subscriber.name, subscriber.audience, subscriber.channel,
             subscriber.contact, watched),
        )
        self._conn.commit()

    def list_subscribers(self, audience: str | None = None) -> list[Subscriber]:
        if audience is None:
            rows = self._conn.execute("SELECT * FROM subscribers").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM subscribers WHERE audience = ?", (audience,)
            ).fetchall()
        return [self._row_to_subscriber(r) for r in rows]

    @staticmethod
    def _row_to_subscriber(row: sqlite3.Row) -> Subscriber:
        watched = set(json.loads(row["watched_ids"])) if row["watched_ids"] else None
        return Subscriber(
            id=row["id"], name=row["name"], audience=row["audience"],
            channel=row["channel"], contact=row["contact"], watched_ids=watched,
        )
