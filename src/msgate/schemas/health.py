"""Health and HA status models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    status: str = Field(..., examples=["healthy"])
    smtp_server: bool = True
    exchange_backend: bool = True
    backend_latency_ms: float = Field(..., examples=[42.5])
    queue_pending: int = 0


class HAModeStatus(BaseModel):
    node_id: str = Field(..., examples=["node-01"])
    role: str = Field(..., examples=["active"], description="'active' or 'passive'")
    vrrp_state: str = Field(..., examples=["MASTER"])
    leader_node: str = Field(..., examples=["node-01"])
