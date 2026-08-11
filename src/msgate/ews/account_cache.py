"""Per-thread EWS Account cache (connection reuse)."""

from __future__ import annotations

import threading
from typing import Any

from exchangelib import Account

from msgate.logging_setup import get_logger

log = get_logger("ews.cache")

_local = threading.local()


def _store() -> dict[tuple[Any, ...], Account]:
    store = getattr(_local, "accounts", None)
    if store is None:
        store = {}
        _local.accounts = store
    return store


def cache_get(key: tuple[Any, ...]) -> Account | None:
    return _store().get(key)


def cache_put(key: tuple[Any, ...], account: Account) -> None:
    _store()[key] = account
    log.debug("EWS account cached key_user=%s", key[1] if len(key) > 1 else "?")


def cache_invalidate(*, username: str | None = None) -> None:
    store = _store()
    if username is None:
        store.clear()
        return
    for key in list(store):
        if len(key) > 1 and key[1] == username:
            del store[key]
