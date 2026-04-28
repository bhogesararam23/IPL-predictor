"""
Utility helpers shared across the IPL Engine backend.

Contains team-name normalisation, safe numeric parsing,
and other small reusable functions.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── canonical name mapping ─────────────────────────────────────────────
# Maps common abbreviations, short forms, and variant spellings to a
# single canonical name used throughout the engine.
TEAM_ALIASES: dict[str, str] = {
    # Chennai Super Kings
    "csk": "Chennai Super Kings",
    "chennai": "Chennai Super Kings",
    "chennai super kings": "Chennai Super Kings",
    # Mumbai Indians
    "mi": "Mumbai Indians",
    "mumbai": "Mumbai Indians",
    "mumbai indians": "Mumbai Indians",
    # Royal Challengers Bengaluru / Bangalore
    "rcb": "Royal Challengers Bengaluru",
    "royal challengers bengaluru": "Royal Challengers Bengaluru",
    "royal challengers bangalore": "Royal Challengers Bengaluru",
    "bengaluru": "Royal Challengers Bengaluru",
    # Kolkata Knight Riders
    "kkr": "Kolkata Knight Riders",
    "kolkata": "Kolkata Knight Riders",
    "kolkata knight riders": "Kolkata Knight Riders",
    # Delhi Capitals
    "dc": "Delhi Capitals",
    "delhi": "Delhi Capitals",
    "delhi capitals": "Delhi Capitals",
    # Rajasthan Royals
    "rr": "Rajasthan Royals",
    "rajasthan": "Rajasthan Royals",
    "rajasthan royals": "Rajasthan Royals",
    # Sunrisers Hyderabad
    "srh": "Sunrisers Hyderabad",
    "hyderabad": "Sunrisers Hyderabad",
    "sunrisers hyderabad": "Sunrisers Hyderabad",
    "sunrisers": "Sunrisers Hyderabad",
    # Punjab Kings
    "pbks": "Punjab Kings",
    "punjab": "Punjab Kings",
    "punjab kings": "Punjab Kings",
    # Gujarat Titans
    "gt": "Gujarat Titans",
    "gujarat": "Gujarat Titans",
    "gujarat titans": "Gujarat Titans",
    # Lucknow Super Giants
    "lsg": "Lucknow Super Giants",
    "lucknow": "Lucknow Super Giants",
    "lucknow super giants": "Lucknow Super Giants",
}


def normalise_team_name(raw: str) -> str:
    """Return the canonical team name for a given raw string.

    Args:
        raw: The raw team name string (possibly abbreviated or misspelt).

    Returns:
        The canonical full team name, or the original string title-cased
        if no alias is found.
    """
    key = raw.strip().lower()
    return TEAM_ALIASES.get(key, raw.strip().title())


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely parse a value to float, returning *default* on failure.

    Args:
        value: The value to convert.
        default: Fallback if conversion fails.

    Returns:
        Parsed float or *default*.
    """
    if value is None:
        return default
    try:
        cleaned = str(value).strip().replace(",", "")
        if cleaned in ("", "-", "–", "—"):
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        logger.debug("Could not parse '%s' as float, using default %s", value, default)
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely parse a value to int, returning *default* on failure.

    Args:
        value: The value to convert.
        default: Fallback if conversion fails.

    Returns:
        Parsed int or *default*.
    """
    if value is None:
        return default
    try:
        cleaned = str(value).strip().replace(",", "")
        if cleaned in ("", "-", "–", "—"):
            return default
        return int(float(cleaned))
    except (ValueError, TypeError):
        logger.debug("Could not parse '%s' as int, using default %s", value, default)
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* between *lo* and *hi* (inclusive).

    Args:
        value: The number to clamp.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        Clamped value.
    """
    return max(lo, min(hi, value))
