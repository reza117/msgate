"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.schemas.health import HealthStatus
from msgate.tls.negotiate import negotiate

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
    exchange_ok = False
    latency = 0.0
    pending = 0

    with state.session_factory() as session:
        pending = state.queue.pending_count(session)

    if cfg.ews is not None:
        try:
            import time

            t0 = time.perf_counter()
            negotiate(cfg.ews)
            latency = (time.perf_counter() - t0) * 1000
            exchange_ok = True
        except Exception:
            exchange_ok = False

    healthy = smtp_ok and exchange_ok
    if not healthy:
        response.status_code = 503

    return HealthStatus(
        status="healthy" if healthy else "degraded",
        smtp_server=smtp_ok,
        exchange_backend=exchange_ok,
        backend_latency_ms=latency,
        queue_pending=pending,
    )
