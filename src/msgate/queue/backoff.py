"""Queue retry helpers."""

from __future__ import annotations

import re

_RETRIABLE_CODES = re.compile(r"\b(429|503|502|504|408)\b")
_RETRIABLE_WORDS = (
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "service unavailable",
    "rate limit",
    "too many requests",
    "connection reset",
    "connection refused",
    "network",
    "unreachable",
)


def is_retriable_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if _RETRIABLE_CODES.search(text):
        return True
    return any(word in text for word in _RETRIABLE_WORDS)


def backoff_seconds(attempts: int, *, base: float = 5.0, maximum: float = 300.0) -> float:
    """Exponential backoff: 5, 10, 20, ... capped at 300s."""
    if attempts < 1:
        attempts = 1
    delay = base * (2 ** (attempts - 1))
    return min(delay, maximum)
