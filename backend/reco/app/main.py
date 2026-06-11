"""FastAPI entry point for the Munch recommendation service.

Phase 0 ships only a health endpoint so the toolchain (ruff, mypy --strict,
pytest) and the Cloud Run container have something real to exercise. The
ranking layers land in Phase 2 (filters, heuristic scorer, eval harness) and
Phase 5 (learned ranker, reason generation).
"""

from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_VERSION = "0.1.0"

app = FastAPI(title="munch-reco", version=SERVICE_VERSION)


class HealthResponse(BaseModel):
    """Liveness payload; `version` lets a deploy be verified from outside."""

    status: str
    version: str


@app.get("/health")
def health() -> HealthResponse:
    # Probed by Cloud Run and by the get-deck edge function. Deliberately
    # dependency-free: a failing database must never mask a live process.
    return HealthResponse(status="ok", version=SERVICE_VERSION)
