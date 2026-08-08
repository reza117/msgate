"""Application bootstrap helpers."""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config as AlembicConfig

from msgate.app.state import AppState
from msgate.auth.admin import admin_exists, bootstrap_admin_from_env
from msgate.config.load import bootstrap_config
from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import resolve_secret_box
from msgate.db.session import make_engine, make_session_factory
from msgate.events import EventHub
from msgate.observability.metrics import MetricsRegistry
from msgate.observability.webhooks import WebhookNotifier
from msgate.paths import db_path
from msgate.queue.service import QueueService
from msgate.queue.worker import QueueWorker


def run_migrations() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = AlembicConfig("alembic.ini")
    # alembic.ini defaults to ./data/msgate.db — always override with MSGATE_DATA_DIR.
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path.resolve()}")
    command.upgrade(cfg, "head")


def build_app_state(*, send_fn=None) -> AppState:
    run_migrations()
    secret_env = os.environ.get("MSGATE_SECRET_KEY")
    box = resolve_secret_box(env_key=secret_env)

    engine = make_engine()
    session_factory = make_session_factory(engine)
    config = bootstrap_config(session_factory, box)

    runtime = RuntimeConfig(config)
    metrics = MetricsRegistry()
    webhooks = WebhookNotifier()
    events = EventHub(metrics=metrics, webhooks=webhooks)
    queue = QueueService(session_factory, runtime, box, send_fn=send_fn, events=events)
    worker = QueueWorker(session_factory, runtime, box, send_fn=send_fn, events=events)

    bootstrap_admin_from_env(session_factory)

    state = AppState(
        runtime=runtime,
        secret_box=box,
        session_factory=session_factory,
        queue=queue,
        worker=worker,
        events=events,
        metrics=metrics,
        webhooks=webhooks,
    )
    state.refresh_metrics()
    return state


def ensure_admin_bootstrap(session_factory) -> bool:
    """Bootstrap admin from env if needed. Returns True if env bootstrap ran."""
    return bootstrap_admin_from_env(session_factory)


def admin_configured(session_factory) -> bool:
    with session_factory() as session:
        return admin_exists(session)
