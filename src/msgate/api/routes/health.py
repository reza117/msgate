"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.drivers.registry import backend_label, check_backend_health
from msgate.schemas.health import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz(state: AppState = Depends(get_state)) -> dict[str, str]:
    if not state.smtp_ok():
        return {"status": "degraded"}
    return {"status": "ok"}


@router.get("/readyz", response_model=HealthStatus)
def readyz(
    response: Response,
    state: AppState = Depends(get_state),
) -> HealthStatus:
    cfg = state.runtime.get()
    smtp_ok = state.smtp_ok()
    pending = 0

    with state.session_factory() as session:
        pending = state.queue.pending_count(session)

    health = check_backend_health(cfg)
    healthy = smtp_ok and health.ok

    if not healthy:
        response.status_code = 503

    return HealthStatus(
        status="healthy" if healthy else "degraded",
        smtp_server=smtp_ok,
        exchange_backend=health.ok,
        backend=health.driver or backend_label(cfg),
        backend_ok=health.ok,
        backend_latency_ms=health.latency_ms,
        queue_pending=pending,
        backend_detail=health.detail or health.error,
    )
