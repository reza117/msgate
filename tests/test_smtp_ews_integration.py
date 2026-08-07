"""SMTP → EWS integration test with mocked EWS sender."""

from __future__ import annotations

import smtplib
import socket
import time
from dataclasses import dataclass

from conftest import memory_session_factory
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.queue.service import QueueService
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig
from msgate.smtp.server import create_controller


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class Captured:
    calls: list[dict]


def _setup_stack(config: GatewayConfig, send_fn):
    captured = Captured(calls=[])

    def wrapped(**kwargs):
        captured.calls.append(kwargs)
        return send_fn(**kwargs)

    _engine, session_factory = memory_session_factory()
    runtime = RuntimeConfig(config)
    box = SecretBox.from_passphrase("test-secret-key-for-unit-tests!!")
    queue = QueueService(session_factory, runtime, box, send_fn=wrapped)
    controller, _auth = create_controller(runtime, queue)
    return controller, captured


def test_smtp_auth_plain_domain_user_reaches_ews_mock() -> None:
    def fake_send(**kwargs):
        class R:
            message_id = "ews-mock-1"
            changekey = None

        return R()

    port = _free_port()
    config = GatewayConfig(
        smtp=SMTPConfig(bind_address="127.0.0.1", port=port, allowed_ips=["127.0.0.1"]),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            domain="WDC",
            trust_self_signed=True,
            primary_smtp="internal.wdc@example.com",
        ),
        default_sender="internal.wdc@example.com",
    )
    controller, captured = _setup_stack(config, fake_send)
    controller.start()
    time.sleep(0.15)
    try:
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = "internal.wdc@example.com"
        msg["To"] = "admin@example.com"
        msg["Subject"] = "auth plain test"
        msg.set_content("hello from msgate test")

        with smtplib.SMTP("127.0.0.1", port, timeout=5) as client:
            client.ehlo()
            client.login(r"WDC\internal.wdc", "s3cret")
            client.send_message(msg)

        assert len(captured.calls) == 1
        call = captured.calls[0]
        assert call["ews_username"] == r"WDC\internal.wdc"
        assert call["password"] == "s3cret"
        assert "admin@example.com" in call["rcpt_tos"]
        assert b"auth plain test" in call["mime_bytes"]
    finally:
        controller.stop()


def test_smtp_anonymous_allowlisted_uses_configured_ews_creds() -> None:
    def fake_send(**kwargs):
        class R:
            message_id = "ews-mock-2"
            changekey = None

        return R()

    port = _free_port()
    config = GatewayConfig(
        smtp=SMTPConfig(bind_address="127.0.0.1", port=port, allowed_ips=["127.0.0.1"]),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            username=r"WDC\svc.msgate",
            password="svc-pass",
            primary_smtp="svc@example.com",
        ),
    )
    controller, captured = _setup_stack(config, fake_send)
    controller.start()
    time.sleep(0.15)
    try:
        payload = (
            "From: zabbix@example.com\r\n"
            "To: admin@example.com\r\n"
            "Subject: anon\r\n\r\n"
            "body\r\n"
        )
        with smtplib.SMTP("127.0.0.1", port, timeout=5) as client:
            client.sendmail("zabbix@example.com", ["admin@example.com"], payload)
        assert len(captured.calls) == 1
        assert captured.calls[0]["ews_username"] == r"WDC\svc.msgate"
        assert captured.calls[0]["password"] == "svc-pass"
    finally:
        controller.stop()
