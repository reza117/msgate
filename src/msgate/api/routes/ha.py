"""High-availability status API."""

from __future__ import annotations

from fastapi import APIRouter

from msgate.observability.ha import read_ha_status
from msgate.schemas.health import HAModeStatus

router = APIRouter(prefix="/api/v1", tags=["ha"])


@router.get("/ha/status", response_model=HAModeStatus)
def ha_status() -> HAModeStatus:
    return read_ha_status()
