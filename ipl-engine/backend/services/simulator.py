"""
Monte Carlo simulation engine for IPL playoff probabilities.

Runs N simulations of the remaining league stage, tracking each team's
finishing position to estimate Top-4 and Top-2 qualification probabilities.

Performance notes
-----------------
- Pydantic model creation is avoided in the inner loop; all per-fixture
  state is tracked in plain dicts and lightweight dataclasses.
- Win probabilities use the ``get_win_probability_fast`` path which
  accepts raw numeric values.
- NRR is tracked via cumulative runs/overs (``NRRState``) rather than
  repeated delta-averaging, matching the real ICC NRR formula.
- Pre-computed base win-rates avoid recomputation across simulations.

Logging
-------
- INFO:  start / progress (every 10%) / completion summary.
- DEBUG: per-fixture match outcome, NRR updates, probability inputs.
"""

from __future__ import annotations

import logging
import random
import time
from collections import defaultdict
from typing import Final

from backend.models.team import (
    Fixture,
    SimulationResponse,
    SimulationResult,
    TeamStanding,
)
from backend.services.nrr import NRRState, clamp_nrr, init_nrr_state, simulate_match_outcome
from backend.services.probability import get_win_probability_fast

logger = logging.getLogger(__name__)

# ── defaults ───────────────────────────────────────────────────────────
DEFAULT_SIMULATIONS: Final[int] = 10_000
NUM_PLAYOFF_SPOTS: Final[int] = 4
NUM_TOP2_SPOTS: Final[int] = 2
PROGRESS_LOG_INTERVAL: Final[float] = 0.10  # log progress every 10%


def _build_lookup(standings: list[TeamStanding]) -> dict[str, TeamStanding]:
    """Create a name → TeamStanding lookup from standings.

    Args:
        standings: List of current team standings.

    Returns:
        Dict mapping team name to TeamStanding.
    """
    return {team.name: team for team in standings}


def _simulate_once(
    team_names: list[str],
    fixtures: list[Fixture],
    known_teams: set[str],
    base_points: dict[str, int],
    base_wins: dict[str, int],
    base_matches: dict[str, int],
    base_nrr_states: dict[str, NRRState],
    base_win_rates: dict[str, float],
    sim_id: int = 0,
) -> dict[str, int]:
    """Run a single simulation of the remaining league stage.

    All mutable state is copied into local dicts at the start.
    For each remaining fixture the outcome is determined by the
    win-probability model plus a random draw.  Points, wins, matches,
    and cumulative NRR are updated incrementally.

    Args:
        team_names: Ordered list of team names.
        fixtures: Remaining matches to simulate.
        known_teams: Set of known team names (for fast membership test).
        base_points: Starting points per team.
        base_wins: Starting wins per team.
        base_matches: Starting matches per team.
        base_nrr_states: Starting NRR states per team.
        base_win_rates: Starting win rates per team.
        sim_id: Simulation number (for debug logging).

    Returns:
        Dict mapping team name to finishing position (1-indexed).
    """
    # ── copy mutable state ────────────────────────────────────────
    points = dict(base_points)
    wins = dict(base_wins)
    matches = dict(base_matches)
    nrr_states: dict[str, NRRState] = {
        name: NRRState(
            runs_for=st.runs_for,
            overs_faced=st.overs_faced,
            runs_against=st.runs_against,
            overs_bowled=st.overs_bowled,
        )
        for name, st in base_nrr_states.items()
    }

    is_debug = logger.isEnabledFor(logging.DEBUG)

    for fix_idx, fixture in enumerate(fixtures):
        team_a = fixture.team_a
        team_b = fixture.team_b

        # Skip if either team is unknown in the standings.
        if team_a not in known_teams or team_b not in known_teams:
            if is_debug:
                logger.debug(
                    "  [sim=%d fix=%d] Skipping unknown: %s vs %s",
                    sim_id, fix_idx, team_a, team_b,
                )
            continue

        # ── compute win probability using raw values ──────────────
        m_a = matches[team_a]
        m_b = matches[team_b]
        wr_a = wins[team_a] / m_a if m_a > 0 else base_win_rates[team_a]
        wr_b = wins[team_b] / m_b if m_b > 0 else base_win_rates[team_b]

        prob_a_wins = get_win_probability_fast(
            a_points=points[team_a],
            a_nrr=clamp_nrr(nrr_states[team_a].nrr),
            a_win_rate=wr_a,
            a_name=team_a,
            b_points=points[team_b],
            b_nrr=clamp_nrr(nrr_states[team_b].nrr),
            b_win_rate=wr_b,
            b_name=team_b,
            venue=fixture.venue,
        )

        a_wins = random.random() < prob_a_wins

        if a_wins:
            winner, loser = team_a, team_b
        else:
            winner, loser = team_b, team_a

        if is_debug:
            logger.debug(
                "  [sim=%d fix=%d] %s vs %s → %s wins (P=%.3f)",
                sim_id, fix_idx, team_a, team_b, winner, prob_a_wins,
            )

        # ── update points and wins ────────────────────────────────
        points[winner] += 2
        wins[winner] += 1

        # ── update NRR via realistic match simulation ─────────────
        simulate_match_outcome(nrr_states[winner], nrr_states[loser])

        # ── update match counts ───────────────────────────────────
        matches[winner] += 1
        matches[loser] += 1

    # ── rank teams by (points desc, nrr desc) ─────────────────────
    teams_sorted = sorted(
        team_names,
        key=lambda t: (points[t], clamp_nrr(nrr_states[t].nrr)),
        reverse=True,
    )

    return {team: rank + 1 for rank, team in enumerate(teams_sorted)}


def run_simulation(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    num_simulations: int = DEFAULT_SIMULATIONS,
) -> SimulationResponse:
    """Run the full Monte Carlo simulation.

    Args:
        standings: Current IPL points table.
        fixtures: Remaining league-stage matches.
        num_simulations: Number of simulations to run (default 10,000).

    Returns:
        ``SimulationResponse`` with per-team probabilities and timing.
    """
    wall_start = time.perf_counter()

    if not standings:
        logger.warning("No standings provided; returning empty results.")
        return SimulationResponse(
            teams=[], simulations_run=0, remaining_matches=0, elapsed_seconds=0.0,
        )

    lookup = _build_lookup(standings)
    team_names = [t.name for t in standings]
    known_teams = set(team_names)

    # ── pre-compute base state (avoids per-sim dict comprehensions) ──
    base_points = {t.name: t.points for t in standings}
    base_wins = {t.name: t.wins for t in standings}
    base_matches = {t.name: t.matches for t in standings}
    base_win_rates = {t.name: t.win_rate for t in standings}

    # Initialise cumulative NRR states from current standings.
    base_nrr_states: dict[str, NRRState] = {
        t.name: init_nrr_state(t.matches, t.nrr) for t in standings
    }

    logger.info(
        "+-- Simulation starting ----------------------------------------"
    )
    logger.info(
        "|  Teams: %d  |  Fixtures: %d  |  Iterations: %d",
        len(team_names), len(fixtures), num_simulations,
    )
    for t in standings:
        logger.info(
            "|  %-30s  Pts=%2d  NRR=%+.3f  W/L=%d/%d  WR=%.2f",
            t.name, t.points, t.nrr, t.wins, t.losses, t.win_rate,
        )
    logger.info(
        "+---------------------------------------------------------------"
    )

    # ── accumulators ──────────────────────────────────────────────────
    top4_counts: dict[str, int] = defaultdict(int)
    top2_counts: dict[str, int] = defaultdict(int)
    rank_sum: dict[str, float] = defaultdict(float)

    next_progress = PROGRESS_LOG_INTERVAL
    sim_phase_start = time.perf_counter()

    for sim_idx in range(num_simulations):
        ranks = _simulate_once(
            team_names=team_names,
            fixtures=fixtures,
            known_teams=known_teams,
            base_points=base_points,
            base_wins=base_wins,
            base_matches=base_matches,
            base_nrr_states=base_nrr_states,
            base_win_rates=base_win_rates,
            sim_id=sim_idx,
        )

        for team, rank in ranks.items():
            rank_sum[team] += rank
            if rank <= NUM_PLAYOFF_SPOTS:
                top4_counts[team] += 1
            if rank <= NUM_TOP2_SPOTS:
                top2_counts[team] += 1

        # ── progress logging (every 10%) ──────────────────────────
        progress = (sim_idx + 1) / num_simulations
        if progress >= next_progress:
            elapsed = time.perf_counter() - sim_phase_start
            rate = (sim_idx + 1) / elapsed if elapsed > 0 else 0
            logger.info(
                "  >> %5.1f%% complete  (%d/%d)  %.0f sims/sec",
                progress * 100, sim_idx + 1, num_simulations, rate,
            )
            next_progress += PROGRESS_LOG_INTERVAL

    sim_elapsed = time.perf_counter() - sim_phase_start

    # ── build results ─────────────────────────────────────────────────
    results: list[SimulationResult] = []
    for team in team_names:
        standing = lookup[team]
        results.append(
            SimulationResult(
                name=team,
                top4_probability=round(
                    top4_counts[team] / num_simulations, 4
                ),
                top2_probability=round(
                    top2_counts[team] / num_simulations, 4
                ),
                avg_position=round(
                    rank_sum[team] / num_simulations, 2
                ),
                current_points=standing.points,
                current_nrr=standing.nrr,
            )
        )

    # Sort by top4 probability descending.
    results.sort(key=lambda r: r.top4_probability, reverse=True)

    total_elapsed = time.perf_counter() - wall_start

    # ── summary log ───────────────────────────────────────────────────
    logger.info(
        "+-- Simulation complete -----------------------------------------"
    )
    logger.info(
        "|  %d iterations in %.2fs  (%.0f sims/sec)",
        num_simulations, sim_elapsed,
        num_simulations / sim_elapsed if sim_elapsed > 0 else 0,
    )
    logger.info("|")
    logger.info(
        "|  %-30s  %8s  %8s  %8s",
        "Team", "Top4%", "Top2%", "AvgPos",
    )
    logger.info("|  " + "-" * 58)
    for r in results:
        logger.info(
            "|  %-30s  %7.1f%%  %7.1f%%  %7.2f",
            r.name, r.top4_probability * 100,
            r.top2_probability * 100, r.avg_position,
        )
    logger.info(
        "|  Total wall-clock time: %.2fs", total_elapsed,
    )
    logger.info(
        "+---------------------------------------------------------------"
    )

    return SimulationResponse(
        teams=results,
        simulations_run=num_simulations,
        remaining_matches=len(fixtures),
        elapsed_seconds=round(total_elapsed, 3),
    )
