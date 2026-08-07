"""In-memory mock driver for tests."""

from __future__ import annotations

from collections.abc import Callable

from msgate.drivers.base import HealthResult, MailDriver, SendRequest, SendResult
from msgate.schemas.config import GatewayConfig
from msgate.schemas.enums import BackendType

MockSendHook = Callable[[SendRequest, GatewayConfig], SendResult]


class MockDriver(MailDriver):
    def __init__(self, *, on_send: MockSendHook | None = None) -> None:
        self.calls: list[SendRequest] = []
        self._on_send = on_send

    @property
    def backend(self) -> BackendType:
        return BackendType.EWS

    def is_configured(self, config: GatewayConfig) -> bool:
        return True

    def send(self, request: SendRequest, config: GatewayConfig) -> SendResult:
        self.calls.append(request)
        if self._on_send:
            return self._on_send(request, config)
        return SendResult(message_id="mock-1", driver="mock")

    def health(self, config: GatewayConfig) -> HealthResult:
        return HealthResult(ok=True, latency_ms=1.0, driver="mock", detail="mock ok")
