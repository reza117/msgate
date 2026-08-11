"""Background queue worker(s)."""

from __future__ import annotations

import os
import threading

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.observability.metrics import MetricsRegistry
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.processor import LegacySendFn, process_row
from msgate.queue.repository import SessionFactory, claim_next
from msgate.schemas.enums import MessageStatus

log = get_logger("queue.worker")


def _worker_count() -> int:
    raw = os.environ.get("MSGATE_QUEUE_WORKERS", "2").strip() or "2"
    try:
        n = int(raw)
    except ValueError:
        n = 2
    return max(1, min(n, 32))


class QueueWorker:
    """One or more threads that claim queued messages and deliver via EWS."""

    def __init__(
        self,
        session_factory: SessionFactory,
        runtime: RuntimeConfig,
        box: SecretBox,
        *,
        poll_interval: float = 2.0,
        workers: int | None = None,
        send_fn: LegacySendFn | None = None,
        events: EventHub | None = None,
        circuit: CircuitBreaker | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._box = box
        self._poll_interval = poll_interval
        self._workers = workers if workers is not None else _worker_count()
        self._send_fn = send_fn
        self._events = events
        self._circuit = circuit or CircuitBreaker()
        self._metrics = metrics
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._threads: list[threading.Thread] = []

    @property
    def circuit(self) -> CircuitBreaker:
        return self._circuit

    def start(self) -> None:
        if self._threads:
            return
        self._stop.clear()
        for i in range(self._workers):
            t = threading.Thread(
                target=self._run,
                name=f"msgate-queue-{i}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        log.info(
            "queue workers started count=%s interval=%ss",
            self._workers,
            self._poll_interval,
        )

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        for t in self._threads:
            t.join(timeout=5.0)
        self._threads.clear()
        log.info("queue workers stopped")

    def wake(self) -> None:
        """Nudge workers after a new message is enqueued."""
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                drained = self._drain()
            except Exception:
                log.exception("queue worker tick failed")
                drained = False
            if drained and not self._stop.is_set():
                continue
            self._wake.wait(timeout=self._poll_interval)
            self._wake.clear()

    def _drain(self) -> bool:
        """Claim and process until idle or circuit open. Returns True if work ran."""
        import time

        did_work = False
        while not self._stop.is_set():
            if not self._circuit.allow():
                log.debug("circuit open — pausing outbound sends")
                return did_work
            with self._session_factory() as session:
                row = claim_next(session)
                if row is None:
                    return did_work
                did_work = True
                if self._metrics:
                    self._metrics.inc_in_flight()
                t0 = time.perf_counter()
                try:
                    process_row(
                        session,
                        row,
                        runtime=self._runtime,
                        box=self._box,
                        send_fn=self._send_fn,
                        events=self._events,
                        already_claimed=True,
                    )
                finally:
                    if self._metrics:
                        self._metrics.dec_in_flight()
                        self._metrics.observe_send_latency_ms(
                            (time.perf_counter() - t0) * 1000,
                        )
                session.refresh(row)
                if row.status == MessageStatus.SENT.value:
                    self._circuit.record_success()
                elif row.status in (
                    MessageStatus.FAILED.value,
                    MessageStatus.RETRYING.value,
                ):
                    self._circuit.record_failure()
        return did_work
