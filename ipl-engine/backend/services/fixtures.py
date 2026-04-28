"""
Fixture extraction for the IPL Playoff Probability Engine.

Attempts to scrape the remaining fixtures from ESPNcricinfo.
Falls back to a hardcoded fixture list when scraping fails.
"""

from __future__ import annotations

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup

from backend.models.team import Fixture, TeamStanding
from backend.utils.helpers import normalise_team_name

logger = logging.getLogger(__name__)

# ── configuration ──────────────────────────────────────────────────────
REQUEST_TIMEOUT: Final[int] = 15
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HEADERS: Final[dict[str, str]] = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}

# ESPNcricinfo schedule page for IPL 2025
FIXTURES_URL: Final[str] = (
    "https://www.espncricinfo.com/series/ipl-2025-1449924/match-schedule-fixtures-and-results"
)


# ── fallback fixtures ─────────────────────────────────────────────────
# Representative remaining fixtures (mid-season). **Update each season.**
FALLBACK_FIXTURES: Final[list[dict]] = [
    {"match_number": 45, "team_a": "Chennai Super Kings", "team_b": "Mumbai Indians", "venue": "Chennai"},
    {"match_number": 46, "team_a": "Rajasthan Royals", "team_b": "Delhi Capitals", "venue": "Jaipur"},
    {"match_number": 47, "team_a": "Kolkata Knight Riders", "team_b": "Sunrisers Hyderabad", "venue": "Kolkata"},
    {"match_number": 48, "team_a": "Punjab Kings", "team_b": "Gujarat Titans", "venue": "Mohali"},
    {"match_number": 49, "team_a": "Lucknow Super Giants", "team_b": "Royal Challengers Bengaluru", "venue": "Lucknow"},
    {"match_number": 50, "team_a": "Mumbai Indians", "team_b": "Rajasthan Royals", "venue": "Mumbai"},
    {"match_number": 51, "team_a": "Delhi Capitals", "team_b": "Chennai Super Kings", "venue": "Delhi"},
    {"match_number": 52, "team_a": "Sunrisers Hyderabad", "team_b": "Punjab Kings", "venue": "Hyderabad"},
    {"match_number": 53, "team_a": "Gujarat Titans", "team_b": "Kolkata Knight Riders", "venue": "Ahmedabad"},
    {"match_number": 54, "team_a": "Royal Challengers Bengaluru", "team_b": "Lucknow Super Giants", "venue": "Bengaluru"},
    {"match_number": 55, "team_a": "Chennai Super Kings", "team_b": "Rajasthan Royals", "venue": "Chennai"},
    {"match_number": 56, "team_a": "Mumbai Indians", "team_b": "Delhi Capitals", "venue": "Mumbai"},
    {"match_number": 57, "team_a": "Kolkata Knight Riders", "team_b": "Punjab Kings", "venue": "Kolkata"},
    {"match_number": 58, "team_a": "Sunrisers Hyderabad", "team_b": "Gujarat Titans", "venue": "Hyderabad"},
    {"match_number": 59, "team_a": "Lucknow Super Giants", "team_b": "Mumbai Indians", "venue": "Lucknow"},
    {"match_number": 60, "team_a": "Royal Challengers Bengaluru", "team_b": "Chennai Super Kings", "venue": "Bengaluru"},
]


def _scrape_fixtures(url: str) -> list[Fixture]:
    """Attempt to scrape match fixtures from the schedule page.

    Args:
        url: Schedule page URL.

    Returns:
        List of ``Fixture`` objects (may be empty on failure).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch fixtures page: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    fixtures: list[Fixture] = []

    # ESPN fixture cards typically use specific class patterns.
    # We look for match cards containing "vs" text.
    match_cards = soup.find_all("div", class_=lambda c: c and "match" in c.lower()) if soup else []

    for idx, card in enumerate(match_cards, start=1):
        try:
            text = card.get_text(" ", strip=True)
            # Attempt to parse "Team A vs Team B" pattern
            if " vs " in text.lower():
                parts = text.lower().split(" vs ")
                if len(parts) >= 2:
                    team_a_raw = parts[0].strip().split("\n")[-1].strip()
                    team_b_raw = parts[1].strip().split("\n")[0].strip()

                    team_a = normalise_team_name(team_a_raw)
                    team_b = normalise_team_name(team_b_raw)

                    # Try to find venue info
                    venue = None
                    venue_el = card.find("span", class_=lambda c: c and "venue" in c.lower())
                    if venue_el:
                        venue = venue_el.get_text(strip=True)

                    fixtures.append(
                        Fixture(
                            match_number=idx,
                            team_a=team_a,
                            team_b=team_b,
                            venue=venue,
                        )
                    )
        except (AttributeError, IndexError) as exc:
            logger.debug("Skipping malformed fixture card: %s", exc)
            continue

    return fixtures


def _generate_remaining_fixtures(
    standings: list[TeamStanding],
    total_matches_per_team: int = 14,
) -> list[Fixture]:
    """Generate plausible remaining fixtures based on current standings.

    When scraping fails and we don't have a reliable fixture list, we
    generate a round-robin-style set of remaining matches based on how
    many games each team still needs to play.

    Args:
        standings: Current team standings.
        total_matches_per_team: Total league-stage matches per team (IPL = 14).

    Returns:
        A list of generated ``Fixture`` objects.
    """
    remaining_counts: dict[str, int] = {}
    for team in standings:
        left = max(0, total_matches_per_team - team.matches)
        remaining_counts[team.name] = left

    teams = [t.name for t in standings]
    fixtures: list[Fixture] = []
    match_num = 1

    # Greedy pairing: pair teams that still have the most remaining games.
    while True:
        # Sort by remaining games (desc)
        available = [(t, remaining_counts[t]) for t in teams if remaining_counts[t] > 0]
        if len(available) < 2:
            break

        available.sort(key=lambda x: x[1], reverse=True)

        paired = False
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                t_a, _ = available[i]
                t_b, _ = available[j]
                if remaining_counts[t_a] > 0 and remaining_counts[t_b] > 0:
                    fixtures.append(
                        Fixture(
                            match_number=match_num,
                            team_a=t_a,
                            team_b=t_b,
                            venue=None,
                        )
                    )
                    remaining_counts[t_a] -= 1
                    remaining_counts[t_b] -= 1
                    match_num += 1
                    paired = True
                    break
            if paired:
                break

        if not paired:
            break

    return fixtures


def get_remaining_fixtures(
    standings: list[TeamStanding] | None = None,
    url: str | None = None,
) -> list[Fixture]:
    """Return the list of remaining IPL fixtures.

    Strategy:
        1. Try live scraping.
        2. Fall back to hardcoded fixtures.
        3. If standings are provided, generate plausible fixtures.

    Args:
        standings: Current standings (used for fixture generation).
        url: Override URL for the schedule page.

    Returns:
        A list of ``Fixture`` objects.
    """
    target = url or FIXTURES_URL

    # Attempt 1: Live scrape
    fixtures = _scrape_fixtures(target)
    if fixtures:
        logger.info("Scraped %d remaining fixtures from %s.", len(fixtures), target)
        return fixtures

    # Attempt 2: Fallback static fixtures
    logger.info("Using fallback fixture list (%d matches).", len(FALLBACK_FIXTURES))
    fallback = [Fixture(**f) for f in FALLBACK_FIXTURES]

    if fallback:
        return fallback

    # Attempt 3: Generate from standings
    if standings:
        generated = _generate_remaining_fixtures(standings)
        logger.info("Generated %d plausible fixtures from standings.", len(generated))
        return generated

    return []
