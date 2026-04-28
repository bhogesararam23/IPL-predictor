"""
API routes for the IPL simulation engine.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.team import SimulationResponse
from backend.services.fixtures import get_remaining_fixtures
from backend.services.scraper import scrape_points_table
from backend.services.simulator import run_simulation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])


@router.get(
    "/simulate",
    response_model=SimulationResponse,
    summary="Run IPL playoff probability simulation",
    description=(
        "Scrapes the current IPL points table and remaining fixtures, "
        "then runs a Monte Carlo simulation to estimate each team's "
        "probability of qualifying for the playoffs (top 4) and "
        "finishing in the top 2."
    ),
    responses={
        200: {
            "description": "Simulation completed successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "teams": [
                            {
                                "name": "Rajasthan Royals",
                                "top4_probability": 0.92,
                                "top2_probability": 0.64,
                                "avg_position": 2.1,
                                "current_points": 14,
                                "current_nrr": 0.468,
                            }
                        ],
                        "simulations_run": 10000,
                        "remaining_matches": 16,
                    }
                }
            },
        },
        500: {"description": "Internal server error during simulation."},
    },
)
async def simulate(
    simulations: Optional[int] = Query(
        default=10_000,
        ge=100,
        le=100_000,
        description="Number of Monte Carlo simulations to run.",
    ),
) -> SimulationResponse:
    """Run the Monte Carlo simulation and return playoff probabilities.

    Args:
        simulations: Number of simulation iterations (100–100,000).

    Returns:
        SimulationResponse with per-team probabilities and metadata.

    Raises:
        HTTPException: 500 if the simulation fails unexpectedly.
    """
    start = time.perf_counter()

    try:
        # Step 1: Scrape current standings.
        logger.info("Fetching current IPL standings...")
        standings = scrape_points_table()
        logger.info("Loaded %d teams from points table.", len(standings))

        # Step 2: Get remaining fixtures.
        logger.info("Fetching remaining fixtures...")
        fixtures = get_remaining_fixtures(standings=standings)
        logger.info("Loaded %d remaining fixtures.", len(fixtures))

        # Step 3: Run simulation.
        logger.info("Running %d simulations...", simulations)
        result = run_simulation(
            standings=standings,
            fixtures=fixtures,
            num_simulations=simulations,
        )

        elapsed = time.perf_counter() - start
        logger.info("Simulation completed in %.2f seconds.", elapsed)

        return result

    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.exception(
            "Simulation failed after %.2f seconds: %s", elapsed, exc
        )
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {exc!s}",
        ) from exc
