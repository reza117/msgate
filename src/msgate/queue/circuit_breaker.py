"""Outbound circuit breaker (protect Exchange from failure storms)."""

from __future__ import annotations

import os
import threading
import time
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class CircuitBreaker:
    """Opens after consecutive failures; cools down, then allows a probe."""

    def __init__(
        self,
        *,
        failure_threshold: int | None = None,
        cooldown_seconds: float | None = None,
    ) -> None:
        self.failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else max(1, _env_int("MSGATE_CIRCUIT_FAILURE_THRESHOLD", 5))
        )
        self.cooldown_seconds = (
            cooldown_seconds
            if cooldown_seconds is not None
            else max(1.0, _env_float("MSGATE_CIRCUIT_COOLDOWN_SECONDS", 60.0))
        )
        self._failures = 0
        self._opened_at = 0.0
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_half_open_unlocked()
            return self._state

    def allow(self) -> bool:
        with self._lock:
            self._maybe_half_open_unlocked()
            return self._state != CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
            self._opened_at = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def _maybe_half_open_unlocked(self) -> None:
        if self._state != CircuitState.OPEN:
            return
        if time.monotonic() - self._opened_at >= self.cooldown_seconds:
            self._state = CircuitState.HALF_OPEN


def queue_max_pending() -> int:
    return max(1, _env_int("MSGATE_QUEUE_MAX_PENDING", 5000))
