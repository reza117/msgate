"""Outbound webhook notifications."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any

from msgate.logging_setup import get_logger

log = get_logger("webhooks")


def webhook_urls_from_env() -> list[str]:
    raw = os.environ.get("MSGATE_WEBHOOK_URLS", "")
    return [u.strip() for u in raw.split(",") if u.strip()]


class WebhookNotifier:
    """Fire-and-forget HTTP POST webhooks for ops events."""

    def __init__(self, urls: list[str] | None = None) -> None:
        self._urls = urls if urls is not None else webhook_urls_from_env()

    @property
    def enabled(self) -> bool:
        return bool(self._urls)

    def notify(self, kind: str, message: str, data: dict[str, Any] | None = None) -> None:
        if not self._urls:
            return
        payload = {
            "source": "msgate",
            "kind": kind,
            "message": message,
            "data": data or {},
        }
        body = json.dumps(payload).encode("utf-8")
        for url in self._urls:
            threading.Thread(
                target=_post,
                args=(url, body),
                name=f"webhook-{kind}",
                daemon=True,
            ).start()

    def on_event(self, kind: str, message: str, data: dict[str, Any]) -> None:
        if kind.startswith("queue.") or kind in {"ews.health", "backend.health"}:
            self.notify(kind, message, data)


def _post(url: str, body: bytes) -> None:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                log.warning("webhook %s returned %s", url, resp.status)
    except urllib.error.URLError as exc:
        log.warning("webhook %s failed: %s", url, exc)
