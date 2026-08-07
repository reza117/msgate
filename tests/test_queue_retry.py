"""Queue retry integration with mocked send."""

from __future__ import annotations

from conftest import memory_session_factory
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.queue.service import QueueService
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
    assert result.status == MessageStatus.RETRYING.value

    with sf() as session:
        from msgate.queue.processor import process_row
        from msgate.queue.repository import list_messages

        rows = list_messages(session)
        assert len(rows) == 1
        rows[0].next_retry_at = None
        session.commit()
        out = process_row(session, rows[0], runtime=runtime, box=box, send_fn=flaky_send)
        assert out is not None
        assert calls["n"] == 2
