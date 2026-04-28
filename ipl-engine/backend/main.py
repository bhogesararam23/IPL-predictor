"""
IPL Playoff Probability Engine — FastAPI Application.

This is the main entrypoint for the backend server.  It configures
logging, CORS, and registers all route modules.
"""

from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.simulate import router as simulate_router

# ── logging setup ──────────────────────────────────────────────────────
# Set IPL_LOG_LEVEL=DEBUG in the environment for granular per-fixture
# and per-simulation logging (very verbose).
_log_level = os.environ.get("IPL_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(
    title="IPL Playoff Probability Engine",
    description=(
        "A real-time Monte Carlo simulation engine that estimates each "
        "IPL team's probability of qualifying for the playoffs (Top 4) "
        "and finishing in the Top 2.  Data is scraped live from "
        "ESPNcricinfo and enriched with a multi-factor probability model."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────
# Allow all origins in development; restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── register routes ───────────────────────────────────────────────────
app.include_router(simulate_router)


@app.get("/", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health-check endpoint.

    Returns:
        Simple status dict confirming the API is alive.
    """
    return {
        "status": "ok",
        "service": "IPL Playoff Probability Engine",
        "version": "1.0.0",
    }


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Alias health endpoint for load balancers / monitoring."""
    return {"status": "healthy"}
