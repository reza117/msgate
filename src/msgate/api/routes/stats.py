"""Dashboard stats JSON API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from msgate.api.deps import get_state
from msgate.api.routes.ui import _stats
from msgate.api.stats import DashboardStats
from msgate.app.state import AppState

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(state: AppState = Depends(get_state)) -> DashboardStats:
    return _stats(state)
