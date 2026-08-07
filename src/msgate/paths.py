"""Filesystem paths for runtime data (DB, logs, secrets, TLS cache)."""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Writable data root.

    Production (systemd): MSGATE_DATA_DIR=/var/lib/msgate
    Dev default: ./data under the process working directory
    """
    raw = os.environ.get("MSGATE_DATA_DIR", "").strip()
    return Path(raw) if raw else Path("data")


def db_path() -> Path:
    return data_dir() / "msgate.db"


def log_dir() -> Path:
    raw = os.environ.get("MSGATE_LOG_DIR", "").strip()
    return Path(raw) if raw else data_dir() / "logs"


def secret_key_path() -> Path:
    return data_dir() / ".secret_key"


def tls_cache_path() -> Path:
    return data_dir() / "tls_cache.json"
