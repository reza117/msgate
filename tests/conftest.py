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
    events = EventHub()
    queue = QueueService(sf, runtime, box, events=events)
    worker = QueueWorker(sf, runtime, box, events=events)
    return AppState(
        runtime=runtime,
        secret_box=box,
        session_factory=sf,
        queue=queue,
        worker=worker,
        events=events,
        smtp_running=True,
        smtp_controller=object(),
    )


def make_test_client(*, authenticated: bool = False) -> TestClient:
    state = make_test_state()
    client = TestClient(create_app(state))
    if authenticated:
        client.post(
            "/ui/auth/setup",
            data={"password": "testpass12", "password_confirm": "testpass12"},
            follow_redirects=False,
        )
    return client
