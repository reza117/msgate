"""Prometheus-style metrics registry."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class MetricsRegistry:
    """Thread-safe counters and gauges for Prometheus export."""

    messages_sent: int = 0
    messages_failed: int = 0
    messages_retried: int = 0
    smtp_connections: int = 0
    smtp_deferred: int = 0
    auth_failures: int = 0
    queue_pending: int = 0
    in_flight: int = 0
    send_latency_ms_sum: float = 0.0
    send_latency_ms_count: int = 0
    send_latency_ms_max: float = 0.0
    backend_up: int = 1
    circuit_open: int = 0
    _start: float = field(default_factory=time.monotonic)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc_sent(self) -> None:
        with self._lock:
            self.messages_sent += 1

    def inc_failed(self) -> None:
        with self._lock:
            self.messages_failed += 1

    def inc_retried(self) -> None:
        with self._lock:
            self.messages_retried += 1

    def inc_auth_failure(self) -> None:
        with self._lock:
            self.auth_failures += 1

    def inc_smtp_deferred(self) -> None:
        with self._lock:
            self.smtp_deferred += 1

    def set_in_flight(self, count: int) -> None:
        with self._lock:
            self.in_flight = max(0, count)

    def inc_in_flight(self) -> None:
        with self._lock:
            self.in_flight += 1

    def dec_in_flight(self) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)

    def observe_send_latency_ms(self, ms: float) -> None:
        with self._lock:
            self.send_latency_ms_sum += max(0.0, ms)
            self.send_latency_ms_count += 1
            if ms > self.send_latency_ms_max:
                self.send_latency_ms_max = ms

    def set_queue_pending(self, count: int) -> None:
        with self._lock:
            self.queue_pending = count

    def set_backend_up(self, ok: bool) -> None:
        with self._lock:
            self.backend_up = 1 if ok else 0

    def set_circuit_open(self, open_: bool) -> None:
        with self._lock:
            self.circuit_open = 1 if open_ else 0

    def on_event(self, kind: str) -> None:
        if kind == "auth.fail":
            self.inc_auth_failure()
        elif kind == "queue.sent":
            self.inc_sent()
        elif kind == "queue.failed":
            self.inc_failed()
        elif kind == "queue.retry":
            self.inc_retried()

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            avg = (
                self.send_latency_ms_sum / self.send_latency_ms_count
                if self.send_latency_ms_count
                else 0.0
            )
            return {
                "messages_sent": float(self.messages_sent),
                "messages_failed": float(self.messages_failed),
                "messages_retried": float(self.messages_retried),
                "auth_failures": float(self.auth_failures),
                "smtp_deferred": float(self.smtp_deferred),
                "queue_pending": float(self.queue_pending),
                "in_flight": float(self.in_flight),
                "send_latency_ms_avg": avg,
                "send_latency_ms_max": float(self.send_latency_ms_max),
                "backend_up": float(self.backend_up),
                "circuit_open": float(self.circuit_open),
                "uptime_seconds": time.monotonic() - self._start,
            }

    def prometheus_text(self) -> str:
        snap = self.snapshot()
        lines = [
            "# HELP msgate_messages_sent_total Messages delivered successfully",
            "# TYPE msgate_messages_sent_total counter",
            f"msgate_messages_sent_total {snap['messages_sent']:.0f}",
            "# HELP msgate_messages_failed_total Messages permanently failed",
            "# TYPE msgate_messages_failed_total counter",
            f"msgate_messages_failed_total {snap['messages_failed']:.0f}",
            "# HELP msgate_messages_retried_total Queue retry attempts",
            "# TYPE msgate_messages_retried_total counter",
            f"msgate_messages_retried_total {snap['messages_retried']:.0f}",
            "# HELP msgate_auth_failures_total SMTP authentication failures",
            "# TYPE msgate_auth_failures_total counter",
            f"msgate_auth_failures_total {snap['auth_failures']:.0f}",
            "# HELP msgate_smtp_deferred_total SMTP 4xx deferrals (queue full / circuit)",
            "# TYPE msgate_smtp_deferred_total counter",
            f"msgate_smtp_deferred_total {snap['smtp_deferred']:.0f}",
            "# HELP msgate_queue_pending Pending queue messages",
            "# TYPE msgate_queue_pending gauge",
            f"msgate_queue_pending {snap['queue_pending']:.0f}",
            "# HELP msgate_in_flight Messages currently being sent",
            "# TYPE msgate_in_flight gauge",
            f"msgate_in_flight {snap['in_flight']:.0f}",
            "# HELP msgate_send_latency_ms_avg Average EWS send latency",
            "# TYPE msgate_send_latency_ms_avg gauge",
            f"msgate_send_latency_ms_avg {snap['send_latency_ms_avg']:.3f}",
            "# HELP msgate_send_latency_ms_max Max EWS send latency",
            "# TYPE msgate_send_latency_ms_max gauge",
            f"msgate_send_latency_ms_max {snap['send_latency_ms_max']:.3f}",
            "# HELP msgate_backend_up Active mail backend health (1=ok)",
            "# TYPE msgate_backend_up gauge",
            f"msgate_backend_up {snap['backend_up']:.0f}",
            "# HELP msgate_circuit_open Outbound circuit breaker open (1=open)",
            "# TYPE msgate_circuit_open gauge",
            f"msgate_circuit_open {snap['circuit_open']:.0f}",
            "# HELP msgate_uptime_seconds Process uptime",
            "# TYPE msgate_uptime_seconds gauge",
            f"msgate_uptime_seconds {snap['uptime_seconds']:.3f}",
        ]
        return "\n".join(lines) + "\n"
