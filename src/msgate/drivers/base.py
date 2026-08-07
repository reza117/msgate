"""Mail driver contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from msgate.schemas.config import GatewayConfig
from msgate.schemas.enums import BackendType


@dataclass(slots=True)
class SendResult:
    message_id: str | None
    changekey: str | None = None
    driver: str | None = None


@dataclass(slots=True)
class SendRequest:
    auth_username: str
    password: str
    mail_from: str
    rcpt_tos: list[str]
    mime_bytes: bytes
    default_sender: str | None = None


@dataclass(slots=True)
class HealthResult:
    ok: bool
    latency_ms: float = 0.0
    detail: str = ""
    error: str | None = None
    driver: str = ""
    extra: dict[str, str] = field(default_factory=dict)


class MailDriver(ABC):
    """Outbound mail backend."""

    @property
    @abstractmethod
    def backend(self) -> BackendType:
        raise NotImplementedError

    @abstractmethod
    def is_configured(self, config: GatewayConfig) -> bool:
        raise NotImplementedError

    @abstractmethod
    def send(self, request: SendRequest, config: GatewayConfig) -> SendResult:
        raise NotImplementedError

    @abstractmethod
    def health(self, config: GatewayConfig) -> HealthResult:
        raise NotImplementedError

    def label(self) -> str:
        return self.backend.value.upper()
