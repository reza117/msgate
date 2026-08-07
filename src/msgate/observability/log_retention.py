"""Log file rotation and retention."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from msgate.logging_setup import get_logger

log = get_logger("log_retention")

DEFAULT_LOG_DIR = Path("data/logs")
DEFAULT_RETENTION_DAYS = 14


def retention_days() -> int:
    raw = os.environ.get("MSGATE_LOG_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_RETENTION_DAYS


def log_dir() -> Path:
    return Path(os.environ.get("MSGATE_LOG_DIR", str(DEFAULT_LOG_DIR)))


def setup_file_logging(level: str = "INFO") -> Path | None:
    """Add rotating daily log file under data/logs. Returns log path if enabled."""
    if os.environ.get("MSGATE_FILE_LOGGING", "true").lower() in {"0", "false", "no"}:
        return None

    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"msgate-{datetime.now(UTC).strftime('%Y%m%d')}.log"

    root = logging.getLogger("msgate")
    if any(isinstance(h, logging.FileHandler) for h in root.handlers):
        return path

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())
    return path


def purge_old_logs() -> int:
    """Delete log files older than retention policy. Returns count removed."""
    days = retention_days()
    cutoff = datetime.now(UTC) - timedelta(days=days)
    removed = 0
    directory = log_dir()
    if not directory.is_dir():
        return 0
    for path in directory.glob("msgate-*.log"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError as exc:
            log.warning("failed to purge %s: %s", path, exc)
    if removed:
        log.info("purged %s log file(s) older than %s days", removed, days)
    return removed
