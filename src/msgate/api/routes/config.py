"""Gateway configuration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.config.export import export_config, import_config
from msgate.config.store import merge_config_update, redact_config, save_config
from msgate.schemas.config import GatewayConfig

router = APIRouter(prefix="/api/v1", tags=["config"])


class ConfigExportResponse(BaseModel):
    bundle: str = Field(..., description="AES-encrypted configuration bundle")


class ConfigImportRequest(BaseModel):
    bundle: str


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
    state.refresh_metrics()
    return redact_config(merged)


@router.post("/config/export", response_model=ConfigExportResponse)
def export_gateway_config(state: AppState = Depends(get_state)) -> ConfigExportResponse:
    bundle = export_config(state.runtime.get(), state.secret_box)
    return ConfigExportResponse(bundle=bundle)


@router.post("/config/import", response_model=GatewayConfig)
def import_gateway_config(
    body: ConfigImportRequest,
    state: AppState = Depends(get_state),
) -> GatewayConfig:
    try:
        config = import_config(body.bundle, state.secret_box)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config bundle: {exc}") from exc
    state.runtime.replace(config)
    with state.session_factory() as session:
        save_config(session, config, state.secret_box)
    state.refresh_metrics()
    return redact_config(config)
