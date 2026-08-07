"""Persistent + in-memory cache of winning TLS profiles per endpoint."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from msgate.logging_setup import get_logger
from msgate.paths import tls_cache_path
from msgate.tls.profiles import TlsProfileId

log = get_logger("tls.cache")

_lock = threading.Lock()
_memory: dict[str, str] = {}


def _default_path() -> Path:
    return tls_cache_path()


def cache_key(
    host: str,
    port: int,
    *,
    tls_mode: str,
    ca_file: str | None,
    trust_self_signed: bool,
) -> str:
    return (
        f"{host.lower()}:{port}|mode={tls_mode}"
        f"|ca={ca_file or ''}|insecure={int(trust_self_signed)}"
    )


def get_cached(key: str, path: Path | None = None) -> TlsProfileId | None:
    with _lock:
        if key in _memory:
            return TlsProfileId(_memory[key])
        store = _load(path or _default_path())
        value = store.get(key)
        if value:
            _memory[key] = value
            return TlsProfileId(value)
    return None


def put_cached(key: str, profile_id: TlsProfileId, path: Path | None = None) -> None:
    with _lock:
        _memory[key] = profile_id.value
        store_path = path or _default_path()
        store = _load(store_path)
        store[key] = profile_id.value
        _save(store_path, store)
    log.info("TLS profile cached key=%s profile=%s", key, profile_id.value)


def invalidate(key: str, path: Path | None = None) -> None:
    with _lock:
        _memory.pop(key, None)
        store_path = path or _default_path()
        store = _load(store_path)
        if key in store:
            del store[key]
            _save(store_path, store)
    log.info("TLS profile cache invalidated key=%s", key)


def clear_memory() -> None:
    with _lock:
        _memory.clear()


def _load(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("TLS cache read failed path=%s err=%s", path, exc)
        return {}


def _save(path: Path, store: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
