"""Database engine helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DB_PATH = Path("data") / "msgate.db"


def make_engine(db_path: Path | str | None = None, *, echo: bool = False) -> Engine:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path.resolve()}"
    return create_engine(
        url,
        echo=echo,
        connect_args={"check_same_thread": False},
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
