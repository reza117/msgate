"""Background capacity watcher — UI signals + optional admin email."""

from __future__ import annotations

import threading
import time

from msgate.app.state import AppState
from msgate.logging_setup import get_logger
from msgate.ops.alert_mail import send_capacity_alert
from msgate.ops.alerts_config import load_ops_alerts
from msgate.ops.capacity import evaluate_capacity

log = get_logger("ops.watcher")


class CapacityWatcher:
    def __init__(self, state: AppState, *, interval: float = 30.0) -> None:
        self._state = state
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_email_at = 0.0
        self._last_level = "ok"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="msgate-capacity",
            daemon=True,
        )
        self._thread.start()
        log.info("capacity watcher started interval=%ss", self._interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        log.info("capacity watcher stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                log.exception("capacity watcher tick failed")
            self._stop.wait(self._interval)

    def _tick(self) -> None:
        state = self._state
        with state.session_factory() as session:
            ops = load_ops_alerts(session)
            pending = state.queue.pending_count(session)
            status = evaluate_capacity(
                session,
                pending=pending,
                circuit=state.circuit,
                ops=ops,
            )
        state.capacity_status = status
        state.refresh_metrics()

        if status.level == "ok":
            self._last_level = "ok"
            return

        if self._events_needed(status):
            state.events.publish_sync(
                "capacity.warn" if status.level == "warn" else "capacity.critical",
                "; ".join(status.reasons) or status.level,
                level=status.level,
                pending=status.pending,
            )

        if (
            ops.email_alerts_enabled
            and ops.admin_email.strip()
            and status.level == "critical"
            and self._email_allowed(ops.alert_cooldown_seconds)
        ):
            if send_capacity_alert(state, status, ops.admin_email.strip()):
                self._last_email_at = time.monotonic()

        self._last_level = status.level

    def _events_needed(self, status) -> bool:
        return status.level != self._last_level

    def _email_allowed(self, cooldown: int) -> bool:
        return time.monotonic() - self._last_email_at >= max(60, cooldown)
