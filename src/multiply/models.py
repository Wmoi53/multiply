"""Core data model: players, clubs, bids and subscribers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Player:
    id: str
    name: str
    age: int
    position: str
    performance_score: float  # 0-100, e.g. per-90 output vs. positional benchmark
    contract_years_remaining: float
    league_tier: int  # 1 = top five European leagues ... 5 = lower tier

    def __post_init__(self) -> None:
        if not 0 <= self.performance_score <= 100:
            raise ValueError("performance_score must be between 0 and 100")
        if self.contract_years_remaining < 0:
            raise ValueError("contract_years_remaining cannot be negative")
        if not 1 <= self.league_tier <= 5:
            raise ValueError("league_tier must be between 1 and 5")


@dataclass
class Club:
    id: str
    name: str
    revenue_eur: float
    net_debt_eur: float
    league_tier: int  # 1 = top five European leagues ... 5 = lower tier
    squad: list[Player] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.league_tier <= 5:
            raise ValueError("league_tier must be between 1 and 5")


@dataclass
class Bid:
    id: str
    target_type: str  # "player" or "club"
    target_id: str
    bidder: str
    amount_eur: float
    verified: bool = False
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.target_type not in ("player", "club"):
            raise ValueError("target_type must be 'player' or 'club'")
        if self.amount_eur <= 0:
            raise ValueError("amount_eur must be positive")


@dataclass
class Subscriber:
    id: str
    name: str
    audience: str  # "investor" or "fan"
    channel: str  # "console", "email" or "webhook"
    contact: str  # email address, webhook URL, or arbitrary handle for console
    watched_ids: set[str] | None = None  # None means "watch everything"

    def __post_init__(self) -> None:
        if self.audience not in ("investor", "fan"):
            raise ValueError("audience must be 'investor' or 'fan'")
        if self.channel not in ("console", "email", "webhook"):
            raise ValueError("channel must be 'console', 'email' or 'webhook'")

    def is_watching(self, target_id: str) -> bool:
        return self.watched_ids is None or target_id in self.watched_ids
