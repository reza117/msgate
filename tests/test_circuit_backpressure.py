"""Circuit breaker and SMTP backpressure tests."""

from __future__ import annotations

from conftest import memory_session_factory
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.observability.metrics import MetricsRegistry
from msgate.queue.circuit_breaker import CircuitBreaker, CircuitState
from msgate.queue.service import QueueService
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig


def test_circuit_opens_after_threshold() -> None:
    br = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
    assert br.allow()
    br.record_failure()
    br.record_failure()
    assert br.state == CircuitState.CLOSED
    br.record_failure()
    assert br.state == CircuitState.OPEN
    assert not br.allow()
    br.record_success()
    assert br.state == CircuitState.CLOSED
    assert br.allow()


def test_backpressure_queue_full() -> None:
    _engine, sf = memory_session_factory()
    cfg = GatewayConfig(
        smtp=SMTPConfig(),
        ews=EWSConfig(server_url="https://mail.example.com/EWS/Exchange.asmx"),
    )
    runtime = RuntimeConfig(cfg)
    box = SecretBox.from_passphrase("bp-test-secret-key-12345678901")
    metrics = MetricsRegistry()
    queue = QueueService(sf, runtime, box, metrics=metrics, max_pending=2)

    for i in range(2):
        queue.accept_smtp(
            client_ip="127.0.0.1",
            raw_auth_user="u",
            sanitized_user="u",
            mail_from="a@example.com",
            rcpt_tos=["b@example.com"],
            mime_bytes=f"Subject: {i}\r\n\r\nx\r\n".encode(),
            ews_username="u",
            password="p",
        )

    defer = queue.check_backpressure()
    assert defer is not None
    assert defer.startswith("452")
    assert metrics.smtp_deferred == 1


def test_backpressure_circuit_open() -> None:
    _engine, sf = memory_session_factory()
    cfg = GatewayConfig(
        smtp=SMTPConfig(),
        ews=EWSConfig(server_url="https://mail.example.com/EWS/Exchange.asmx"),
    )
    runtime = RuntimeConfig(cfg)
    box = SecretBox.from_passphrase("bp-test-secret-key-12345678901")
    metrics = MetricsRegistry()
    queue = QueueService(sf, runtime, box, metrics=metrics, max_pending=100)
    br = CircuitBreaker(failure_threshold=1, cooldown_seconds=60)
    br.record_failure()
    assert br.state == CircuitState.OPEN

    defer = queue.check_backpressure(circuit=br)
    assert defer is not None
    assert defer.startswith("451")
    assert "circuit" in defer.lower()
