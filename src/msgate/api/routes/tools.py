"""Tools API: auth simulator, backend health."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException

from msgate.api.backend import require_backend_credentials
from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.drivers.base import HealthResult
from msgate.drivers.registry import backend_label, check_backend_health
from msgate.tools.diagnostics import (
    AuthSimRequest,
    AuthSimResult,
    EwsHealthResult,
    check_ews_health,
    simulate_auth,
)

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.post("/auth-simulate", response_model=AuthSimResult)
def auth_simulate(
    mechanism: str = Form(default="PLAIN"),
    payload: str = Form(...),
    state: AppState = Depends(get_state),
) -> AuthSimResult:
    cfg = state.runtime.get()
    domain = cfg.ews.domain if cfg.ews else None
    req = AuthSimRequest(mechanism=mechanism, payload=payload, default_domain=domain)
    result = simulate_auth(req)
    state.events.publish_sync(
        "auth.sim",
        f"Auth sim {mechanism}: {'ok' if result.ok else 'fail'}",
        raw=result.raw_user,
        ews_user=result.ews_username,
    )
    return result


@router.get("/backend-health", response_model=HealthResult)
def backend_health(state: AppState = Depends(get_state)) -> HealthResult:
    cfg = state.runtime.get()
    result = check_backend_health(cfg)
    state.events.publish_sync(
        "backend.health",
        f"{backend_label(cfg)} health {'ok' if result.ok else 'fail'}",
        detail=result.detail or result.error,
    )
    return result


@router.post("/ews-health", response_model=EwsHealthResult)
def ews_health(state: AppState = Depends(get_state)) -> EwsHealthResult:
    """Legacy alias for EWS-only health check."""
    cfg = state.runtime.get()
    ews = cfg.ews
    if ews is None or not ews.username or not ews.password:
        raise HTTPException(status_code=400, detail="EWS username/password required in config")
    result = check_ews_health(ews, username=ews.username, password=ews.password)
    state.events.publish_sync(
        "ews.health",
        "EWS health ok" if result.ok else "EWS health fail",
        detail=result.detail or result.error,
    )
    return result


@router.post("/send-test")
def send_test_ui(
    sender: str = Form(...),
    recipients: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    state: AppState = Depends(get_state),
) -> dict[str, str]:
    username, password = require_backend_credentials(state)
    rcpts = [r.strip() for r in recipients.split(",") if r.strip()]
    result = state.queue.submit_test(
        sender=sender,
        recipients=rcpts,
        subject=subject,
        body=body,
        is_html=False,
        ews_username=username,
        password=password,
    )
    state.events.publish_sync("test.send", f"Test email queued {result.message_id}")
    return {"message_id": result.message_id, "status": result.status}
