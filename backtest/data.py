"""Historical fixture data model + loaders for the backtest harness.

A :class:`BacktestFixture` bundles everything the ``ah_decision`` engine needs
to make a decision (odds, model fair probabilities, the home handicap line, and
an optional time-ordered odds series) together with the *settled outcome* --
the final score. Settling from the final score (rather than a pre-baked
win/loss flag) keeps Asian-Handicap settlement unambiguous.

Two loaders are provided:

* :func:`load_fixtures_csv` -- one fixture per row (see column schema below).
* :func:`load_fixtures_json` -- a JSON list of objects with the same fields.

Both reuse :class:`ah_decision.conditions.OddsSnapshot` for movement series.

CSV column schema
-----------------
Required columns (header names, order-independent):

    label        str    fixture identifier / label (e.g. "Arsenal v Spurs")
    home_odds    float  decimal odds for the home side of the AH market
    away_odds    float  decimal odds for the away side of the AH market
    fair_home    float  model fair probability for home (0..1)
    fair_away    float  model fair probability for away (0..1)
    line         float  home-side handicap (e.g. -0.5, +0.25, -1.0)
    home_goals   int    final goals scored by home
    away_goals   int    final goals scored by away

Optional columns:

    league       str    competition, for segment breakdowns
    kickoff      str    ISO datetime string (free-form; stored as-is)
    bookmaker    str    book the price came from
    snapshots    str    time-ordered odds series, encoded as
                        "ts:home_odds:away_odds|ts:home_odds:away_odds|..."
                        e.g. "0:1.90:2.05|60:1.84:2.00|120:1.78:1.95"

JSON schema
-----------
A top-level list of objects using the same field names. ``snapshots`` there is
a list of objects: ``[{"ts": 0, "home_odds": 1.90, "away_odds": 2.05}, ...]``.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field

from ah_decision.conditions import OddsSnapshot

__all__ = [
    "BacktestFixture",
    "parse_snapshots_field",
    "load_fixtures_csv",
    "load_fixtures_json",
]


@dataclass
class BacktestFixture:
    """One historical fixture: engine inputs + the settled final score."""

    label: str
    home_odds: float
    away_odds: float
    fair_home: float
    fair_away: float
    line: float                       # home-side handicap
    home_goals: int
    away_goals: int
    snapshots: list[OddsSnapshot] = field(default_factory=list)
    # Optional metadata for segment breakdowns.
    league: str | None = None
    kickoff: str | None = None
    bookmaker: str | None = None

    def odds_for(self, side: str) -> float:
        """Decimal odds for ``'home'`` or ``'away'``."""
        if side == "home":
            return self.home_odds
        if side == "away":
            return self.away_odds
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")


def parse_snapshots_field(raw: str) -> list[OddsSnapshot]:
    """Parse the CSV ``snapshots`` string into a list of :class:`OddsSnapshot`.

    Format: ``"ts:home_odds:away_odds|ts:home_odds:away_odds|..."``. Empty or
    whitespace-only input yields an empty list.
    """
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []
    snaps: list[OddsSnapshot] = []
    for chunk in text.split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"snapshot chunk {chunk!r} must be 'ts:home_odds:away_odds'"
            )
        ts, home_odds, away_odds = parts
        snaps.append(
            OddsSnapshot(
                ts=float(ts),
                home_odds=float(home_odds),
                away_odds=float(away_odds),
            )
        )
    return snaps


def _clean(value) -> str | None:
    """Normalize an optional metadata cell: strip strings, treat empty as None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fixture_from_mapping(row: dict) -> BacktestFixture:
    """Build a fixture from a dict of already-typed-or-string values."""
    snaps_raw = row.get("snapshots")
    if isinstance(snaps_raw, list):
        snapshots = [
            OddsSnapshot(
                ts=float(s["ts"]),
                home_odds=float(s["home_odds"]),
                away_odds=float(s["away_odds"]),
            )
            for s in snaps_raw
        ]
    else:
        snapshots = parse_snapshots_field(snaps_raw if isinstance(snaps_raw, str) else "")

    return BacktestFixture(
        label=str(row["label"]).strip(),
        home_odds=float(row["home_odds"]),
        away_odds=float(row["away_odds"]),
        fair_home=float(row["fair_home"]),
        fair_away=float(row["fair_away"]),
        line=float(row["line"]),
        home_goals=int(float(row["home_goals"])),
        away_goals=int(float(row["away_goals"])),
        snapshots=snapshots,
        league=_clean(row.get("league")),
        kickoff=_clean(row.get("kickoff")),
        bookmaker=_clean(row.get("bookmaker")),
    )


def load_fixtures_csv(path: str) -> list[BacktestFixture]:
    """Load fixtures from a CSV file. See module docstring for the schema."""
    fixtures: list[BacktestFixture] = []
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Skip fully blank rows.
            if not any((v or "").strip() for v in row.values()):
                continue
            fixtures.append(_fixture_from_mapping(row))
    return fixtures


def load_fixtures_json(path: str) -> list[BacktestFixture]:
    """Load fixtures from a JSON file (a list of objects; see module docstring)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("fixtures JSON must be a list of fixture objects")
    return [_fixture_from_mapping(obj) for obj in data]
