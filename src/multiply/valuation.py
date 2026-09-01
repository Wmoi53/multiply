"""Transparent, first-principles valuation heuristics for players and clubs.

These are deliberately simple, explainable multiplier models rather than a
black-box ML fit: every factor is named and bounded so investors and fans can
see *why* a number moved, which is the point of the auto-notification layer
in ``service.py``. Swap in richer models later without touching callers --
the public functions (`estimate_player_value`, `estimate_club_value`) are the
seam.
"""

from __future__ import annotations

from .models import Club, Player

# Reference anchor: a peak-age, strong-performing player in a top-five league
# on a long contract. Everything else is a multiplier off this base.
BASE_PLAYER_VALUE_EUR = 20_000_000.0

LEAGUE_TIER_MULTIPLIER = {1: 1.00, 2: 0.75, 3: 0.55, 4: 0.40, 5: 0.25}

# Enterprise value trades at a higher multiple of revenue in leagues with
# bigger broadcast/commercial ecosystems.
REVENUE_MULTIPLE_BY_TIER = {1: 4.5, 2: 3.0, 3: 2.0, 4: 1.5, 5: 1.0}

# How much of aggregate squad market value gets added on top of the
# revenue-multiple figure when computing club enterprise value. Squad value
# already partially shows up in future revenue expectations (better squad ->
# better results -> more broadcast/commercial revenue), so it is blended in
# at a discount rather than added in full to avoid double-counting.
SQUAD_VALUE_WEIGHT = 0.5


def age_factor(age: int) -> float:
    """Career value curve: rises to a peak around 26-27, decays either side."""
    if age <= 17:
        return 0.35
    if age <= 20:
        return 0.55 + (age - 17) * 0.0667  # -> ~0.75 at 20
    if age <= 26:
        return 0.75 + (age - 20) * 0.0417  # -> ~1.00 at 26
    if age <= 29:
        return 1.00 - (age - 26) * 0.05  # -> ~0.85 at 29
    if age <= 33:
        return 0.85 - (age - 29) * 0.10  # -> ~0.45 at 33
    return max(0.15, 0.45 - (age - 33) * 0.08)


def performance_multiplier(performance_score: float) -> float:
    """Maps a 0-100 performance score onto a 0.4x-1.6x multiplier."""
    return 0.4 + (performance_score / 100.0) * 1.2


def contract_multiplier(years_remaining: float) -> float:
    """Shorter remaining contracts carry Bosman/free-transfer risk -> discount."""
    if years_remaining <= 0:
        return 0.30
    if years_remaining >= 4:
        return 1.00
    # linear ramp from 0.30 at 0 years to 1.00 at 4 years
    return 0.30 + (years_remaining / 4.0) * 0.70


def league_multiplier(league_tier: int) -> float:
    return LEAGUE_TIER_MULTIPLIER[league_tier]


def estimate_player_value(player: Player) -> float:
    """Estimated market value in EUR for a single player."""
    return (
        BASE_PLAYER_VALUE_EUR
        * age_factor(player.age)
        * performance_multiplier(player.performance_score)
        * contract_multiplier(player.contract_years_remaining)
        * league_multiplier(player.league_tier)
    )


def estimate_squad_value(club: Club) -> float:
    return sum(estimate_player_value(p) for p in club.squad)


def estimate_club_value(club: Club) -> float:
    """Estimated club enterprise ("face") value in EUR.

    value = revenue x league revenue-multiple
          + squad market value x overlap-correction weight
          - net debt
    """
    revenue_component = club.revenue_eur * REVENUE_MULTIPLE_BY_TIER[club.league_tier]
    squad_component = estimate_squad_value(club) * SQUAD_VALUE_WEIGHT
    return revenue_component + squad_component - club.net_debt_eur
