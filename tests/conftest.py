"""Shared pytest fixtures and DB helpers."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from msgate.api.app import create_app
from msgate.app.state import AppState
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.db.models import AdminUserRow, Base, MessageRow, SettingRow  # noqa: F401
from msgate.events import EventHub
from msgate.observability.metrics import MetricsRegistry
from msgate.observability.webhooks import WebhookNotifier
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.service import QueueService
from msgate.queue.worker import QueueWorker
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig


def memory_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)


def make_test_state(*, with_ews: bool = True) -> AppState:
    _engine, sf = memory_session_factory()
    ews = None
    if with_ews:
        ews = EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            username="svc@example.com",
            password="secret",
            trust_self_signed=True,
        )
    cfg = GatewayConfig(smtp=SMTPConfig(), ews=ews)
    runtime = RuntimeConfig(cfg)
    box = SecretBox.from_passphrase("test-secret-key-123456789012345")
    metrics = MetricsRegistry()
    webhooks = WebhookNotifier()
    events = EventHub(metrics=metrics, webhooks=webhooks)
    circuit = CircuitBreaker()
    worker = QueueWorker(sf, runtime, box, events=events, circuit=circuit)
    queue = QueueService(
        sf,
        runtime,
        box,
        events=events,
        wake=worker.wake,
        metrics=metrics,
    )
    return AppState(
        runtime=runtime,
        secret_box=box,
        session_factory=sf,
        queue=queue,
        worker=worker,
        events=events,
        metrics=metrics,
        webhooks=webhooks,
        circuit=circuit,
        smtp_running=True,
        smtp_controller=object(),
    )


def make_test_client(*, authenticated: bool = False) -> TestClient:
    state = make_test_state()
    client = TestClient(create_app(state))
    if authenticated:
        _ensure_logged_in(client)
    return client


def _ensure_logged_in(client: TestClient, password: str = "testpass12") -> None:
    from msgate.auth.admin import admin_exists, create_admin

    state = client.app.state.msgate
    with state.session_factory() as session:
        if not admin_exists(session):
            create_admin(session, password, must_change_password=False)
    resp = client.post(
        "/ui/auth/login",
        data={"password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    assert client.get("/api/v1/config").status_code == 200
