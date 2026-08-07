"""Thread-safe runtime gateway configuration."""

from __future__ import annotations

import threading

from msgate.schemas.config import GatewayConfig


class RuntimeConfig:
    """Mutable config snapshot shared by SMTP handler, worker, and API."""

    def __init__(self, initial: GatewayConfig) -> None:
        self._lock = threading.RLock()
        self._config = initial

    def get(self) -> GatewayConfig:
        with self._lock:
            return self._config.model_copy(deep=True)

    def replace(self, config: GatewayConfig) -> None:
        with self._lock:
            self._config = config

    def update(self, config: GatewayConfig) -> None:
        with self._lock:
            self._config = config
