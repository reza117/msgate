"""Gateway configuration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.config.store import merge_config_update, redact_config, save_config
from msgate.schemas.config import GatewayConfig

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/config", response_model=GatewayConfig)
def get_config(state: AppState = Depends(get_state)) -> GatewayConfig:
    return redact_config(state.runtime.get())


@router.put("/config", response_model=GatewayConfig)
def put_config(
    update: GatewayConfig,
    state: AppState = Depends(get_state),
) -> GatewayConfig:
    current = state.runtime.get()
    merged = merge_config_update(current, update)
    state.runtime.replace(merged)
    with state.session_factory() as session:
        save_config(session, merged, state.secret_box)
    return redact_config(merged)
