"""Database URL helpers."""

from __future__ import annotations

import os
from pathlib import Path

from msgate.db.url import is_sqlite_url, resolve_database_url


def test_default_sqlite_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MSGATE_DATABASE_URL", raising=False)
    monkeypatch.setenv("MSGATE_DATA_DIR", str(tmp_path))
    url = resolve_database_url()
    assert url.startswith("sqlite:///")
    assert is_sqlite_url(url)
    assert (tmp_path / "msgate.db").parent == tmp_path or "msgate.db" in url


def test_explicit_postgres_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "MSGATE_DATABASE_URL",
        "postgresql+psycopg://msgate:secret@db:5432/msgate",
    )
    url = resolve_database_url()
    assert url.startswith("postgresql+")
    assert not is_sqlite_url(url)


def test_make_engine_sqlite(tmp_path: Path, monkeypatch) -> None:
    from msgate.db.session import make_engine

    monkeypatch.delenv("MSGATE_DATABASE_URL", raising=False)
    engine = make_engine(tmp_path / "t.db")
    assert engine.dialect.name == "sqlite"
    engine.dispose()
