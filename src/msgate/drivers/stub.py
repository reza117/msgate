"""Placeholder drivers for backends not yet implemented."""

from __future__ import annotations

from msgate.drivers.base import HealthResult, MailDriver, SendRequest, SendResult
from msgate.schemas.config import GatewayConfig
from msgate.schemas.enums import BackendType


class _StubDriver(MailDriver):
    def __init__(self, backend: BackendType, config_attr: str) -> None:
        self._backend = backend
        self._config_attr = config_attr
        self._phase = "4b" if backend == BackendType.GRAPH else "4c"

    @property
    def backend(self) -> BackendType:
        return self._backend

    def is_configured(self, config: GatewayConfig) -> bool:
        return getattr(config, self._config_attr) is not None

    def send(self, request: SendRequest, config: GatewayConfig) -> SendResult:
        raise NotImplementedError(f"{self.label()} driver not implemented (Phase {self._phase})")

    def health(self, config: GatewayConfig) -> HealthResult:
        if not self.is_configured(config):
            return HealthResult(
                ok=False,
                driver=self.backend.value,
                error=f"{self.label()} not configured",
            )
        return HealthResult(
            ok=False,
            driver=self.backend.value,
            error=f"{self.label()} driver not implemented (Phase {self._phase})",
        )


class GraphDriver(_StubDriver):
    def __init__(self) -> None:
        super().__init__(BackendType.GRAPH, "graph")


class GmailDriver(MailDriver):
    @property
    def backend(self) -> BackendType:
        return BackendType.GMAIL

    def is_configured(self, config: GatewayConfig) -> bool:
        return False

    def send(self, request: SendRequest, config: GatewayConfig) -> SendResult:
        raise NotImplementedError("Gmail driver not implemented (Phase 4c)")

    def health(self, config: GatewayConfig) -> HealthResult:
        return HealthResult(
            ok=False,
            driver=self.backend.value,
            error="Gmail driver not implemented (Phase 4c)",
        )
