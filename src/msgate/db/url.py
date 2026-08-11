"""Database URL resolution (SQLite default, optional Postgres)."""

from __future__ import annotations

import os
from pathlib import Path

from msgate.paths import db_path


def resolve_database_url(*, db_path_arg: Path | str | None = None) -> str:
    """Return SQLAlchemy URL.

    Prefer ``MSGATE_DATABASE_URL`` (e.g. ``postgresql+psycopg://user:pass@host/db``).
    Otherwise use SQLite under ``MSGATE_DATA_DIR`` / ``./data``.
    """
    raw = os.environ.get("MSGATE_DATABASE_URL", "").strip()
    if raw:
        return raw
    path = Path(db_path_arg) if db_path_arg else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve()}"


def is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite:")
