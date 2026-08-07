"""Driver lookup and health helpers."""

from __future__ import annotations

from msgate.drivers.base import HealthResult, MailDriver
from msgate.drivers.ews import EwsDriver
from msgate.drivers.stub import GmailDriver, GraphDriver
from msgate.schemas.config import GatewayConfig
from msgate.schemas.enums import BackendType

_DRIVERS: dict[BackendType, MailDriver] = {
    BackendType.EWS: EwsDriver(),
    BackendType.GRAPH: GraphDriver(),
    BackendType.GMAIL: GmailDriver(),
}


def get_driver(backend: BackendType | str) -> MailDriver:
    key = BackendType(backend)
    driver = _DRIVERS.get(key)
    if driver is None:
        raise ValueError(f"unknown backend: {backend}")
    return driver


def resolve_driver(config: GatewayConfig) -> MailDriver:
    return get_driver(config.backend)


def check_backend_health(config: GatewayConfig) -> HealthResult:
    driver = resolve_driver(config)
    if not driver.is_configured(config):
        return HealthResult(
            ok=False,
            driver=driver.backend.value,
            error=f"{driver.label()} not configured",
        )
    return driver.health(config)


def backend_label(config: GatewayConfig) -> str:
    return resolve_driver(config).label()
