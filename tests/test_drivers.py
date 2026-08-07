"""Mail driver tests."""

from __future__ import annotations

from msgate.drivers.base import SendRequest, SendResult
from msgate.drivers.ews import EwsDriver
from msgate.drivers.mock import MockDriver
from msgate.drivers.registry import check_backend_health, get_driver
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig
from msgate.schemas.enums import BackendType


def test_registry_ews_driver() -> None:
    driver = get_driver(BackendType.EWS)
    assert isinstance(driver, EwsDriver)
    assert driver.label() == "EWS"


def test_registry_graph_stub_not_configured() -> None:
    cfg = GatewayConfig(smtp=SMTPConfig(), backend=BackendType.GRAPH)
    health = check_backend_health(cfg)
    assert health.ok is False
    assert "not configured" in (health.error or "").lower()


def test_mock_driver_records_calls() -> None:
    driver = MockDriver()
    cfg = GatewayConfig(
        smtp=SMTPConfig(),
        ews=EWSConfig(server_url="https://exchange.example.com/EWS/Exchange.asmx"),
    )
    req = SendRequest(
        auth_username="user@example.com",
        password="pass",
        mail_from="user@example.com",
        rcpt_tos=["a@example.com"],
        mime_bytes=b"raw",
    )
    result = driver.send(req, cfg)
    assert result.message_id == "mock-1"
    assert len(driver.calls) == 1
    assert driver.calls[0].auth_username == "user@example.com"


def test_mock_driver_custom_hook() -> None:
    def hook(req: SendRequest, cfg: GatewayConfig) -> SendResult:
        return SendResult(message_id="custom", driver="mock")

    driver = MockDriver(on_send=hook)
    cfg = GatewayConfig(
        smtp=SMTPConfig(),
        ews=EWSConfig(server_url="https://exchange.example.com/EWS/Exchange.asmx"),
    )
    result = driver.send(
        SendRequest(
            auth_username="u",
            password="p",
            mail_from="u@x.com",
            rcpt_tos=["b@x.com"],
            mime_bytes=b"x",
        ),
        cfg,
    )
    assert result.message_id == "custom"


def test_ews_driver_not_configured() -> None:
    driver = EwsDriver()
    cfg = GatewayConfig(smtp=SMTPConfig(), backend=BackendType.EWS, ews=None)
    health = driver.health(cfg)
    assert health.ok is False
