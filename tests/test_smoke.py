"""Smoke tests for Phase 0 scaffold."""

from msgate import __version__
from msgate.schemas import GatewayConfig, SMTPConfig


def test_version_present() -> None:
    assert __version__


def test_default_gateway_config() -> None:
    cfg = GatewayConfig(smtp=SMTPConfig())
    assert cfg.backend == "ews"
    assert cfg.smtp.port == 1025
    assert cfg.smtp.bind_address == "127.0.0.1"
