"""Database engine helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from msgate.db.url import is_sqlite_url, resolve_database_url


def make_engine(
    db_path_arg: Path | str | None = None,
    *,
    url: str | None = None,
    echo: bool = False,
) -> Engine:
    resolved = url or resolve_database_url(db_path_arg=db_path_arg)

    if is_sqlite_url(resolved):
        engine = create_engine(
            resolved,
            echo=echo,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragma(dbapi_conn, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        return engine

    # Postgres / other: pool_pre_ping survives idle disconnects under load.
    return create_engine(resolved, echo=echo, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
