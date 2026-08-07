"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from msgate.api.deps import get_state
from msgate.app.state import AppState

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(state: AppState = Depends(get_state)) -> PlainTextResponse:
    state.refresh_metrics()
    return PlainTextResponse(
        content=state.metrics.prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
