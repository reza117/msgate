"""Background queue worker."""

from __future__ import annotations

import threading

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.queue.processor import LegacySendFn, process_row
from msgate.queue.repository import SessionFactory, pending_messages

log = get_logger("queue.worker")


class QueueWorker:
    def __init__(
        self,
        session_factory: SessionFactory,
        runtime: RuntimeConfig,
        box: SecretBox,
        *,
        poll_interval: float = 2.0,
        send_fn: LegacySendFn | None = None,
        events: EventHub | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._box = box
        self._poll_interval = poll_interval
        self._send_fn = send_fn
        self._events = events
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="msgate-queue", daemon=True)
        self._thread.start()
        log.info("queue worker started interval=%ss", self._poll_interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        log.info("queue worker stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                log.exception("queue worker tick failed")
            self._stop.wait(self._poll_interval)

    def _tick(self) -> None:
        with self._session_factory() as session:
            rows = pending_messages(session, limit=20)
            for row in rows:
                if self._stop.is_set():
                    break
                process_row(
                    session,
                    row,
                    runtime=self._runtime,
                    box=self._box,
                    send_fn=self._send_fn,
                    events=self._events,
                )

    def wake(self) -> None:
        """Nudge worker (no-op; poll picks up soon)."""
        pass
