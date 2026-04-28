"""
Pydantic models for the IPL Playoff Probability Engine.

Defines all data structures used across the application, ensuring
type safety and automatic validation at API boundaries.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TeamStanding(BaseModel):
    """Represents a team's current standing in the IPL points table."""

    name: str = Field(..., description="Full team name")
    matches: int = Field(0, ge=0, description="Total matches played")
    wins: int = Field(0, ge=0, description="Total wins")
    losses: int = Field(0, ge=0, description="Total losses")
    no_results: int = Field(0, ge=0, description="No-result matches")
    points: int = Field(0, ge=0, description="Total points")
    nrr: float = Field(0.0, description="Net Run Rate")

    # ── cumulative NRR tracking ────────────────────────────────────
    # These are used by the simulation engine for realistic NRR
    # calculations.  When populated, true NRR = (runs_for / overs_faced)
    # - (runs_against / overs_bowled).  Optional for backward compat.
    runs_for: float = Field(0.0, description="Total runs scored across all innings")
    overs_faced: float = Field(0.0, description="Total overs faced across all innings")
    runs_against: float = Field(0.0, description="Total runs conceded across all innings")
    overs_bowled: float = Field(0.0, description="Total overs bowled across all innings")

    @property
    def win_rate(self) -> float:
        """Calculate the team's win rate."""
        if self.matches == 0:
            return 0.0
        return self.wins / self.matches

    @property
    def computed_nrr(self) -> float:
        """Calculate NRR from cumulative overs/runs data.

        Falls back to the ``nrr`` field if cumulative data is absent.
        """
        if self.overs_faced > 0 and self.overs_bowled > 0:
            return (
                self.runs_for / self.overs_faced
                - self.runs_against / self.overs_bowled
            )
        return self.nrr


class Fixture(BaseModel):
    """Represents a remaining / upcoming match."""

    match_number: int | None = Field(None, description="Match number in the season")
    team_a: str = Field(..., description="First team name")
    team_b: str = Field(..., description="Second team name")
    venue: str | None = Field(None, description="Match venue")
    date: str | None = Field(None, description="Match date string")


class SimulationResult(BaseModel):
    """Aggregated playoff probability result for a single team."""

    name: str = Field(..., description="Team name")
    top4_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probability of finishing in the top 4"
    )
    top2_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probability of finishing in the top 2"
    )
    avg_position: float = Field(
        ..., ge=1.0, description="Average finishing position across all simulations"
    )
    current_points: int = Field(0, ge=0, description="Current points in the table")
    current_nrr: float = Field(0.0, description="Current NRR")


class SimulationResponse(BaseModel):
    """Top-level API response for the /simulate endpoint."""

    teams: list[SimulationResult] = Field(
        ..., description="Simulation results for each team"
    )
    simulations_run: int = Field(
        ..., ge=0, description="Number of Monte Carlo simulations executed"
    )
    remaining_matches: int = Field(
        ..., ge=0, description="Number of remaining matches simulated"
    )
    elapsed_seconds: float = Field(
        0.0, ge=0.0, description="Wall-clock time for the simulation in seconds"
    )
