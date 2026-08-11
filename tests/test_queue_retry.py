"""Queue retry integration with mocked send."""

from __future__ import annotations

import time

from conftest import memory_session_factory
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.processor import process_row
from msgate.queue.repository import claim_next, list_messages
from msgate.queue.service import QueueService
from msgate.queue.worker import QueueWorker
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig
from msgate.schemas.enums import MessageStatus


def test_queue_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky_send(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("503 Service Unavailable")

        class R:
            message_id = "ok"
            changekey = None

        return R()

    _engine, sf = memory_session_factory()
    cfg = GatewayConfig(
        smtp=SMTPConfig(),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            primary_smtp="zabbix@example.com",
        ),
    )
    runtime = RuntimeConfig(cfg)
    box = SecretBox.from_passphrase("retry-test-secret-key-1234567")
    # No background worker during insert — avoid SQLite race with claim_next.
    queue = QueueService(sf, runtime, box, send_fn=flaky_send)

    result = queue.accept_smtp(
        client_ip="127.0.0.1",
        raw_auth_user=r"WDC\zabbix",
        sanitized_user="zabbix",
        mail_from="zabbix@example.com",
        rcpt_tos=["admin@example.com"],
        mime_bytes=b"From: zabbix@example.com\r\nSubject: t\r\n\r\nb\r\n",
        ews_username=r"WDC\zabbix",
        password="pw",
    )
    assert result.delivered is False
    assert result.status == MessageStatus.QUEUED.value

    with sf() as session:
        row = claim_next(session)
        assert row is not None
        process_row(
            session,
            row,
            runtime=runtime,
            box=box,
            send_fn=flaky_send,
            already_claimed=True,
        )
        session.refresh(row)
        assert row.status == MessageStatus.RETRYING.value
        row.next_retry_at = None
        session.commit()

    worker = QueueWorker(
        sf,
        runtime,
        box,
        send_fn=flaky_send,
        workers=1,
        poll_interval=0.05,
        circuit=CircuitBreaker(failure_threshold=100, cooldown_seconds=1),
    )
    worker.start()
    try:
        worker.wake()
        deadline = time.time() + 2.0
        while time.time() < deadline:
            with sf() as session:
                rows = list_messages(session)
                if rows and rows[0].status == MessageStatus.SENT.value:
                    assert calls["n"] == 2
                    return
            time.sleep(0.05)
        raise AssertionError(f"expected SENT, calls={calls['n']}")
    finally:
        worker.stop()
