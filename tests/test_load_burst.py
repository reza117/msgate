"""In-process SMTP burst test (load harness smoke)."""

from __future__ import annotations

import smtplib
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.message import EmailMessage

from conftest import memory_session_factory
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.observability.metrics import MetricsRegistry
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.service import QueueService
from msgate.queue.worker import QueueWorker
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig
from msgate.smtp.server import create_controller


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_smtp_burst_accepts_under_concurrency() -> None:
    """Concurrent SMTP DATA must enqueue (fast-accept) without client 5xx."""
    port = _free_port()
    config = GatewayConfig(
        smtp=SMTPConfig(bind_address="127.0.0.1", port=port, allowed_ips=["127.0.0.1"]),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            username="svc@example.com",
            password="secret",
            trust_self_signed=True,
        ),
    )
    _engine, sf = memory_session_factory()
    runtime = RuntimeConfig(config)
    box = SecretBox.from_passphrase("test-secret-key-for-unit-tests!!")
    events = EventHub(metrics=MetricsRegistry())
    circuit = CircuitBreaker()
    sends = 0

    def fake_send(**_kwargs):
        nonlocal sends
        sends += 1

        class R:
            message_id = "mock"
            changekey = None

        return R()

    worker = QueueWorker(
        sf,
        runtime,
        box,
        send_fn=fake_send,
        workers=1,
        poll_interval=0.05,
        events=events,
        circuit=circuit,
    )
    queue = QueueService(
        sf,
        runtime,
        box,
        events=events,
        wake=worker.wake,
        metrics=MetricsRegistry(),
    )
    controller, _auth = create_controller(runtime, queue, events=events, circuit=circuit)
    controller.start()
    try:
        count = 40
        concurrency = 10

        def send_one(i: int) -> str:
            msg = EmailMessage()
            msg["From"] = "zabbix@example.com"
            msg["To"] = "ops@example.com"
            msg["Subject"] = f"burst {i}"
            msg.set_content("x")
            with smtplib.SMTP("127.0.0.1", port, timeout=10) as smtp:
                smtp.send_message(msg)
            return "ok"

        # Accept-only phase: no worker yet (avoids StaticPool races under burst).
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = [pool.submit(send_one, i) for i in range(count)]
            results = [f.result() for f in as_completed(futs)]
        assert results.count("ok") == count
        with sf() as session:
            assert queue.pending_count(session) == count

        worker.start()
        deadline = time.time() + 15
        while time.time() < deadline:
            with sf() as session:
                pending = queue.pending_count(session)
            if pending == 0 and sends == count:
                break
            time.sleep(0.05)
        assert sends == count
        with sf() as session:
            assert queue.pending_count(session) == 0
    finally:
        controller.stop()
        worker.stop()
