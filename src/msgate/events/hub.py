"""Live traffic event hub for WebSocket UI."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from msgate.observability.metrics import MetricsRegistry
    from msgate.observability.webhooks import WebhookNotifier


@dataclass(slots=True)
class TrafficEvent:
    kind: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "message": self.message,
                "data": self.data,
                "ts": self.ts,
            }
        )


class EventHub:
    """Thread-safe fan-out of traffic events to WebSocket subscribers."""

    def __init__(
        self,
        *,
        history_size: int = 200,
        metrics: MetricsRegistry | None = None,
        webhooks: WebhookNotifier | None = None,
    ) -> None:
        self._history: deque[TrafficEvent] = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()
        self.auth_errors_24h = 0
        self._metrics = metrics
        self._webhooks = webhooks

    def publish_sync(self, kind: str, message: str, **data: Any) -> None:
        event = TrafficEvent(kind=kind, message=message, data=data)
        self._history.append(event)
        if kind == "auth.fail":
            self.auth_errors_24h += 1
        if self._metrics:
            self._metrics.on_event(kind)
        if self._webhooks:
            self._webhooks.on_event(kind, message, data)
        payload = event.to_json()
        dead: list[asyncio.Queue[str]] = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.add(q)
            for event in self._history:
                await q.put(event.to_json())
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    def history(self) -> list[TrafficEvent]:
        return list(self._history)
