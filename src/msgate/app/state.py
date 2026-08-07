"""Shared application state for API + SMTP + worker."""

from __future__ import annotations

from dataclasses import dataclass

from aiosmtpd.controller import Controller
from sqlalchemy.orm import sessionmaker

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
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
    smtp_controller: Controller | None = None
    smtp_running: bool = False

    def smtp_ok(self) -> bool:
        return self.smtp_running and self.smtp_controller is not None
