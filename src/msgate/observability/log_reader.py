"""Read and search msgate log files on disk."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from msgate.paths import log_dir

_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}) "
    r"(?P<level>[A-Z]+) "
    r"\[(?P<logger>[^\]]+)\] "
    r"(?P<message>.*)$"
)


@dataclass(frozen=True, slots=True)
class LogEntry:
    ts: str
    level: str
    logger: str
    message: str
    source: str
    raw: str


def list_log_files(*, directory: Path | None = None) -> list[Path]:
    root = directory or log_dir()
    if not root.is_dir():
        return []
    return sorted(root.glob("msgate-*.log"), reverse=True)


def search_logs(
    *,
    query: str = "",
    level: str = "",
    logger: str = "",
    day: str = "",
    limit: int = 200,
    directory: Path | None = None,
) -> list[LogEntry]:
    """Return newest-first matching lines (best-effort parse)."""
    limit = max(1, min(int(limit), 2000))
    q = query.strip().lower()
    level_u = level.strip().upper()
    logger_q = logger.strip().lower()
    day = day.strip()

    files = list_log_files(directory=directory)
    if day:
        files = [p for p in files if day in p.name]

    out: list[LogEntry] = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in reversed(lines):
            if not raw.strip():
                continue
            entry = _parse_line(raw, source=path.name)
            if level_u and entry.level != level_u:
                continue
            if logger_q and logger_q not in entry.logger.lower():
                continue
            if q and q not in entry.raw.lower():
                continue
            out.append(entry)
            if len(out) >= limit:
                return out
    return out


def _parse_line(raw: str, *, source: str) -> LogEntry:
    m = _LINE_RE.match(raw)
    if not m:
        return LogEntry(
            ts="",
            level="",
            logger="",
            message=raw,
            source=source,
            raw=raw,
        )
    return LogEntry(
        ts=m.group("ts"),
        level=m.group("level"),
        logger=m.group("logger"),
        message=m.group("message"),
        source=source,
        raw=raw,
    )


def today_log_stem() -> str:
    return datetime.now(UTC).strftime("%Y%m%d")
