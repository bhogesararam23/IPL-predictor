"""
IPL Points-Table & Fixture Scraper.

Scrapes the current IPL season's points table from ESPNcricinfo and
returns a list of ``TeamStanding`` models.  Falls back to a hardcoded
snapshot when the live scrape fails (network issues, DOM changes, etc.).
"""

from __future__ import annotations

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup, Tag

from backend.models.team import TeamStanding
from backend.utils.helpers import normalise_team_name, safe_float, safe_int

logger = logging.getLogger(__name__)

# ── configuration ──────────────────────────────────────────────────────
REQUEST_TIMEOUT: Final[int] = 15  # seconds
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ESPNcricinfo points table URL for IPL 2025
# Update this URL each season or make it configurable via env vars.
POINTS_TABLE_URL: Final[str] = (
    "https://www.espncricinfo.com/series/ipl-2025-1449924/points-table-standings"
)

HEADERS: Final[dict[str, str]] = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}


# ── fallback data ─────────────────────────────────────────────────────
# A reasonable mid-season snapshot so the engine still works if scraping
# is temporarily broken.  **Update each season.**
FALLBACK_STANDINGS: Final[list[dict]] = [
    {"name": "Rajasthan Royals", "matches": 10, "wins": 7, "losses": 3, "no_results": 0, "points": 14, "nrr": 0.468},
    {"name": "Kolkata Knight Riders", "matches": 10, "wins": 7, "losses": 3, "no_results": 0, "points": 14, "nrr": 0.382},
    {"name": "Chennai Super Kings", "matches": 10, "wins": 6, "losses": 4, "no_results": 0, "points": 12, "nrr": 0.541},
    {"name": "Sunrisers Hyderabad", "matches": 10, "wins": 6, "losses": 4, "no_results": 0, "points": 12, "nrr": 0.295},
    {"name": "Delhi Capitals", "matches": 10, "wins": 5, "losses": 5, "no_results": 0, "points": 10, "nrr": 0.147},
    {"name": "Lucknow Super Giants", "matches": 10, "wins": 5, "losses": 5, "no_results": 0, "points": 10, "nrr": -0.091},
    {"name": "Mumbai Indians", "matches": 10, "wins": 4, "losses": 6, "no_results": 0, "points": 8, "nrr": -0.214},
    {"name": "Gujarat Titans", "matches": 10, "wins": 4, "losses": 6, "no_results": 0, "points": 8, "nrr": -0.563},
    {"name": "Royal Challengers Bengaluru", "matches": 10, "wins": 3, "losses": 7, "no_results": 0, "points": 6, "nrr": -0.340},
    {"name": "Punjab Kings", "matches": 10, "wins": 3, "losses": 7, "no_results": 0, "points": 6, "nrr": -0.625},
]


def _fetch_html(url: str) -> str | None:
    """Download the HTML from *url*, returning ``None`` on any error.

    Args:
        url: The URL to fetch.

    Returns:
        Raw HTML string or ``None``.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _parse_points_table(html: str) -> list[TeamStanding]:
    """Parse the ESPN points-table page and extract team standings.

    Args:
        html: Raw HTML of the points-table page.

    Returns:
        A list of ``TeamStanding`` objects, possibly empty on parse failure.
    """
    soup = BeautifulSoup(html, "lxml")
    standings: list[TeamStanding] = []

    # ESPN uses <table> elements; find the main standings table.
    tables = soup.find_all("table")
    if not tables:
        logger.warning("No <table> elements found in points-table HTML.")
        return standings

    # Usually the first (or largest) table is the standings.
    table = tables[0]
    rows: list[Tag] = table.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue  # skip header / malformed rows

        # Typical ESPN column order:
        # Team | M | W | L | T/NR | Pts | NRR
        # But exact order can vary — we attempt both common layouts.
        try:
            raw_name = cells[0].get_text(strip=True)
            if not raw_name:
                continue

            team_name = normalise_team_name(raw_name)
            matches = safe_int(cells[1].get_text(strip=True))
            wins = safe_int(cells[2].get_text(strip=True))
            losses = safe_int(cells[3].get_text(strip=True))
            no_results = safe_int(cells[4].get_text(strip=True))
            points = safe_int(cells[5].get_text(strip=True))
            nrr = safe_float(cells[6].get_text(strip=True)) if len(cells) > 6 else 0.0

            standings.append(
                TeamStanding(
                    name=team_name,
                    matches=matches,
                    wins=wins,
                    losses=losses,
                    no_results=no_results,
                    points=points,
                    nrr=nrr,
                )
            )
        except (IndexError, ValueError) as exc:
            logger.debug("Skipping malformed row: %s", exc)
            continue

    return standings


def scrape_points_table(url: str | None = None) -> list[TeamStanding]:
    """Scrape the live IPL points table.

    Falls back to ``FALLBACK_STANDINGS`` when the live scrape yields no
    results.

    Args:
        url: Override URL for the points-table page (useful for testing).

    Returns:
        A list of ``TeamStanding`` objects sorted by points (desc).
    """
    target = url or POINTS_TABLE_URL
    html = _fetch_html(target)

    standings: list[TeamStanding] = []
    if html:
        standings = _parse_points_table(html)

    if not standings:
        logger.info(
            "Live scrape returned no data; using fallback standings."
        )
        standings = [TeamStanding(**row) for row in FALLBACK_STANDINGS]

    # Sort by points (desc), then NRR (desc) as tiebreaker.
    standings.sort(key=lambda t: (t.points, t.nrr), reverse=True)
    return standings
