"""Public schema exports."""

from msgate.schemas.config import EWSConfig, GatewayConfig, GraphConfig, SMTPConfig
from msgate.schemas.enums import AuthType, BackendType, MessageStatus
from msgate.schemas.health import HAModeStatus, HealthStatus
from msgate.schemas.messages import EmailMessageRequest, MessageRecord

__all__ = [
    "AuthType",
    "BackendType",
    "EWSConfig",
    "EmailMessageRequest",
    "GatewayConfig",
    "GraphConfig",
    "HAModeStatus",
    "HealthStatus",
    "MessageRecord",
    "MessageStatus",
    "SMTPConfig",
]
