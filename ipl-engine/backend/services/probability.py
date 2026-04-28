"""
Win-probability model for the IPL Playoff Probability Engine.

Calculates the probability that *team_a* beats *team_b* in a given
match, using multiple contextual signals blended into a single
probability score.

Provides both a full-fidelity function (``get_win_probability``) that
accepts Pydantic models, and a lightweight function
(``get_win_probability_fast``) that accepts raw values for use in the
simulation hot loop — avoiding Pydantic model creation overhead.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.models.team import TeamStanding
from backend.utils.helpers import clamp

logger = logging.getLogger(__name__)

# ── tuning constants ───────────────────────────────────────────────────
# These weights control how much each factor influences the final
# probability.  They should be tuned against historical data in a
# production system.

POINTS_WEIGHT: float = 0.35       # influence of points difference
NRR_WEIGHT: float = 0.25          # influence of NRR difference
FORM_WEIGHT: float = 0.25         # influence of recent form (win-rate)
HOME_ADVANTAGE: float = 0.05      # flat bonus for home team

# Maximum deviations used for normalisation.
MAX_POINTS_DIFF: float = 14.0     # theoretical max in a 14-game season
MAX_NRR_DIFF: float = 3.0         # realistic NRR spread
MAX_FORM_DIFF: float = 1.0        # win-rate is [0, 1]


@dataclass(frozen=True)
class MatchContext:
    """Optional contextual signals for a specific match-up.

    Attributes:
        venue: Venue name (used to detect home advantage).
        team_a_home_venues: Venues considered "home" for team A.
        team_b_home_venues: Venues considered "home" for team B.
    """

    venue: str | None = None
    team_a_home_venues: list[str] = field(default_factory=list)
    team_b_home_venues: list[str] = field(default_factory=list)


# ── default home-venue mapping ────────────────────────────────────────
HOME_VENUES: dict[str, list[str]] = {
    "Chennai Super Kings": ["Chennai", "Chepauk", "MA Chidambaram"],
    "Mumbai Indians": ["Mumbai", "Wankhede"],
    "Royal Challengers Bengaluru": ["Bengaluru", "Bangalore", "Chinnaswamy"],
    "Kolkata Knight Riders": ["Kolkata", "Eden Gardens"],
    "Delhi Capitals": ["Delhi", "Arun Jaitley", "Feroz Shah Kotla"],
    "Rajasthan Royals": ["Jaipur", "Sawai Mansingh"],
    "Sunrisers Hyderabad": ["Hyderabad", "Rajiv Gandhi"],
    "Punjab Kings": ["Mohali", "Dharamsala", "Mullanpur"],
    "Gujarat Titans": ["Ahmedabad", "Narendra Modi"],
    "Lucknow Super Giants": ["Lucknow", "Ekana"],
}

# ── pre-computed home venue lookup (lowercase) ────────────────────────
# Built once at import time to avoid repeated lower() calls in the
# hot loop. Maps team name → frozenset of lowercase venue keywords.
_HOME_VENUE_LOWER: dict[str, frozenset[str]] = {
    team: frozenset(v.lower() for v in venues)
    for team, venues in HOME_VENUES.items()
}


def _normalised_signal(diff: float, max_diff: float) -> float:
    """Map a raw difference to [-1, 1] by dividing by the max.

    Args:
        diff: Raw difference (A – B).
        max_diff: Maximum expected absolute difference for normalisation.

    Returns:
        Normalised signal in [-1, 1].
    """
    if max_diff == 0:
        return 0.0
    return clamp(diff / max_diff, -1.0, 1.0)


def _detect_home_advantage(
    team_a: str,
    team_b: str,
    venue: str | None,
) -> float:
    """Return a probability offset for home advantage.

    Positive means *team_a* is at home; negative means *team_b*.

    Args:
        team_a: Name of the first team.
        team_b: Name of the second team.
        venue: Match venue string (may be None).

    Returns:
        Home-advantage offset in [-HOME_ADVANTAGE, +HOME_ADVANTAGE].
    """
    if venue is None:
        return 0.0

    venue_lower = venue.lower()
    a_homes = _HOME_VENUE_LOWER.get(team_a, frozenset())
    b_homes = _HOME_VENUE_LOWER.get(team_b, frozenset())

    a_is_home = any(h in venue_lower for h in a_homes)
    b_is_home = any(h in venue_lower for h in b_homes)

    if a_is_home and not b_is_home:
        return HOME_ADVANTAGE
    if b_is_home and not a_is_home:
        return -HOME_ADVANTAGE
    return 0.0


def get_win_probability(
    team_a: TeamStanding,
    team_b: TeamStanding,
    context: MatchContext | None = None,
) -> float:
    """Calculate the probability that *team_a* wins the match.

    The model blends multiple contextual signals:
      - **Points difference**: teams higher on the table win more often.
      - **NRR difference**: better NRR correlates with dominance.
      - **Form (win-rate)**: recent-ish performance matters.
      - **Home advantage**: small flat bonus for the home team.

    Each signal is normalised to [-1, 1] and weighted.  The aggregate
    is shifted around a 0.5 base, then clamped to [0.05, 0.95] to
    avoid impossible certainties.

    Args:
        team_a: Standing data for the first team.
        team_b: Standing data for the second team.
        context: Optional match context (venue, etc.).

    Returns:
        Probability in [0.05, 0.95] that *team_a* wins.
    """
    venue = context.venue if context else None
    return get_win_probability_fast(
        a_points=team_a.points,
        a_nrr=team_a.nrr,
        a_win_rate=team_a.win_rate,
        a_name=team_a.name,
        b_points=team_b.points,
        b_nrr=team_b.nrr,
        b_win_rate=team_b.win_rate,
        b_name=team_b.name,
        venue=venue,
    )


def get_win_probability_fast(
    a_points: int,
    a_nrr: float,
    a_win_rate: float,
    a_name: str,
    b_points: int,
    b_nrr: float,
    b_win_rate: float,
    b_name: str,
    venue: str | None = None,
) -> float:
    """Lightweight win probability — accepts raw values, no Pydantic overhead.

    Identical logic to ``get_win_probability`` but designed for the
    simulation hot loop where creating Pydantic ``TeamStanding`` objects
    per-fixture per-simulation is prohibitively expensive.

    Args:
        a_points: Team A's current points.
        a_nrr: Team A's current NRR.
        a_win_rate: Team A's win rate (0.0–1.0).
        a_name: Team A's canonical name.
        b_points: Team B's current points.
        b_nrr: Team B's current NRR.
        b_win_rate: Team B's win rate (0.0–1.0).
        b_name: Team B's canonical name.
        venue: Match venue (may be None).

    Returns:
        Probability in [0.05, 0.95] that *team_a* wins.
    """
    # ── 1. points signal ───────────────────────────────────────────
    points_signal = _normalised_signal(a_points - b_points, MAX_POINTS_DIFF)

    # ── 2. NRR signal ──────────────────────────────────────────────
    nrr_signal = _normalised_signal(a_nrr - b_nrr, MAX_NRR_DIFF)

    # ── 3. form signal ─────────────────────────────────────────────
    form_signal = _normalised_signal(a_win_rate - b_win_rate, MAX_FORM_DIFF)

    # ── 4. home advantage ──────────────────────────────────────────
    home_offset = _detect_home_advantage(a_name, b_name, venue)

    # ── aggregate ──────────────────────────────────────────────────
    weighted_sum = (
        POINTS_WEIGHT * points_signal
        + NRR_WEIGHT * nrr_signal
        + FORM_WEIGHT * form_signal
    )

    probability = 0.5 + weighted_sum / 2 + home_offset

    # Clamp to avoid 0% or 100% certainty.
    probability = clamp(probability, 0.05, 0.95)

    logger.debug(
        "%s vs %s → P(A wins)=%.3f  [pts=%.2f nrr=%.2f form=%.2f home=%.2f]",
        a_name,
        b_name,
        probability,
        points_signal,
        nrr_signal,
        form_signal,
        home_offset,
    )

    return probability
