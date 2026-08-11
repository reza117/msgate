"""Shared application state for API + SMTP + worker."""

from __future__ import annotations

from dataclasses import dataclass

from aiosmtpd.controller import Controller
from sqlalchemy.orm import sessionmaker

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.observability.metrics import MetricsRegistry
from msgate.observability.webhooks import WebhookNotifier
from msgate.ops.capacity import CapacityStatus
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.service import QueueService
from msgate.queue.worker import QueueWorker


@dataclass
class AppState:
    runtime: RuntimeConfig
    secret_box: SecretBox
    session_factory: sessionmaker
    queue: QueueService
    worker: QueueWorker
    events: EventHub
    metrics: MetricsRegistry
    webhooks: WebhookNotifier
    circuit: CircuitBreaker
    smtp_controller: Controller | None = None
    smtp_running: bool = False
    capacity_status: CapacityStatus | None = None
    capacity_watcher: object | None = None
    digest_scheduler: object | None = None

    def smtp_ok(self) -> bool:
        return self.smtp_running and self.smtp_controller is not None

    def refresh_metrics(self) -> None:
        with self.session_factory() as session:
            self.metrics.set_queue_pending(self.queue.pending_count(session))
        self.metrics.set_circuit_open(self.circuit.state.value == "open")
        from msgate.drivers.registry import check_backend_health

        health = check_backend_health(self.runtime.get())
        self.metrics.set_backend_up(health.ok)
