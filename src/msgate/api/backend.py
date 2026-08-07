"""Backend credential helpers for API routes."""

from __future__ import annotations

from fastapi import HTTPException

from msgate.app.state import AppState
from msgate.drivers.registry import resolve_driver


def require_backend_credentials(state: AppState) -> tuple[str, str]:
    cfg = state.runtime.get()
    driver = resolve_driver(cfg)
    if not driver.is_configured(cfg):
        raise HTTPException(status_code=400, detail=f"{driver.label()} not configured")
    if cfg.backend == "ews":
        ews = cfg.ews
        if ews is None or not ews.username or not ews.password:
            raise HTTPException(status_code=400, detail="EWS credentials required")
        return ews.username, ews.password
    raise HTTPException(status_code=400, detail=f"{driver.label()} test send not available yet")
