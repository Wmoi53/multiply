"""Configuration for the Asian-Handicap decision engine.

Every threshold used by the engine lives here as a ``Config`` field with a
sensible default, so the whole engine runs with zero external dependencies.
``Config.from_yaml`` can layer overrides from a YAML file; PyYAML is imported
lazily so the runtime stays standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

__all__ = ["Config"]


@dataclass
class Config:
    """Thresholds governing the required-edge, movement, and staking rules.

    Percentages are in percentage points of probability (e.g. 1.5 == 1.5%),
    odds are decimal, and stake fractions are fractions of bankroll.
    """

    # --- core edge gates ---
    min_abs_edge_pct: float = 1.5        # baseline edge required to bet
    edge_floor_pct: float = 0.5          # hard floor; threshold never drops below this
    max_overround_pct: float = 6.0       # skip markets juicier than this

    # --- extreme price handling ---
    extreme_low_odds: float = 1.50       # below this = very short price
    extreme_high_odds: float = 3.50      # above this = very long price
    extreme_edge_pct: float = 2.5        # required edge at extreme prices

    # --- price-skew handling ---
    short_fav_odds: float = 1.65         # <= this is a short favorite
    long_dog_odds: float = 2.40          # >= this is a long underdog
    price_skew_edge_pct: float = 3.0     # required edge for skewed prices

    # --- deep handicap lines ---
    deep_line_threshold: float = 1.5     # |line| >= this is a deep AH line
    deep_line_edge_pct: float = 2.0      # required edge on deep lines

    # --- side selection ---
    tie_breaker_delta_pct: float = 0.3   # if edges within this, favor price further from 2.0

    # --- recent-market-condition signals ---
    movement_stable_band_pct: float = 0.5   # |delta| below this = 'stable'
    steam_threshold_pct: float = 2.0        # |delta| at/above this = steam
    steam_velocity_pct: float = 1.5         # last-step velocity at/above this = steam
    movement_confirm_discount_pct: float = 0.5  # lower bar when market confirms our side
    steam_confirm_extra_pct: float = 0.5        # extra discount when the confirm is steam
    movement_adverse_bump_pct: float = 1.0      # raise bar when market moves against us
    steam_adverse_extra_pct: float = 0.5        # extra bump when the adverse move is steam

    # --- stake sizing (fractional Kelly) ---
    kelly_multiplier: float = 0.25       # quarter-Kelly for safe compounding
    max_stake_fraction: float = 0.05     # cap any single stake at 5% of bankroll

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Build a ``Config`` from a flat ``key: value`` YAML file.

        Only keys matching ``Config`` fields are applied; everything else in
        the file is ignored. PyYAML is used if available, otherwise a tiny
        built-in parser handles the simple flat format we ship. This keeps the
        runtime dependency-light while still supporting overrides.
        """
        text = _read_text(path)
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text) or {}
        except ImportError:
            data = _parse_flat_yaml(text)

        if not isinstance(data, dict):
            raise ValueError(f"YAML at {path} must be a mapping of key: value")

        valid = {f.name: f.type for f in fields(cls)}
        overrides: dict[str, float] = {}
        for key, value in data.items():
            if key in valid and value is not None:
                overrides[key] = float(value)
        return cls(**overrides)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_flat_yaml(text: str) -> dict[str, float]:
    """Minimal parser for a flat ``key: value`` YAML (numbers only).

    Handles comments (``#``), blank lines, and inline trailing comments.
    Not a general YAML parser -- only the simple config file we ship.
    """
    result: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        # strip inline comment
        value = value.split("#", 1)[0].strip()
        if not value:
            continue
        value = value.strip().strip('"').strip("'")
        try:
            result[key] = float(value)
        except ValueError:
            # non-numeric value -- skip (engine only uses numeric thresholds)
            continue
    return result
