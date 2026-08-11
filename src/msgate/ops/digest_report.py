"""Collect digest statistics for a time window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from msgate.db.models import MessageRow
from msgate.schemas.enums import MessageStatus


@dataclass(frozen=True, slots=True)
class DigestReport:
    period: str  # "daily" | "weekly" | "manual"
    window_start: datetime
    window_end: datetime
    sent: int
    failed: int
    pending: int
    retrying: int
    max_delay_seconds: float | None
    max_delay_message_id: str | None
    max_delay_why: str | None
    top_errors: tuple[str, ...]
    critical_notes: tuple[str, ...]

    def subject(self, template: str) -> str:
        return (
            template.replace("{period}", self.period)
            .replace("{from}", self.window_start.strftime("%Y-%m-%d"))
            .replace("{to}", self.window_end.strftime("%Y-%m-%d"))
        )

    def body_lines(self) -> list[str]:
        lines = [
            f"msgate {self.period} digest",
            f"Window (UTC): {self.window_start.isoformat()} → {self.window_end.isoformat()}",
            "",
            f"Sent: {self.sent}",
            f"Failed: {self.failed}",
            f"Pending now: {self.pending}",
            f"Retrying now: {self.retrying}",
            "",
        ]
        if self.max_delay_seconds is not None:
            lines.append(
                f"Max delivery delay: {self.max_delay_seconds:.0f}s "
                f"(id={self.max_delay_message_id or '—'})"
            )
            if self.max_delay_why:
                lines.append(f"  why: {self.max_delay_why}")
        else:
            lines.append("Max delivery delay: —")
        lines.append("")
        if self.critical_notes:
            lines.append("Critical / notable:")
            lines.extend(f"- {n}" for n in self.critical_notes)
            lines.append("")
        if self.top_errors:
            lines.append("Top failure reasons:")
            lines.extend(f"- {e}" for e in self.top_errors)
        return lines


def collect_digest(
    session: Session,
    *,
    period: str,
    window_start: datetime,
    window_end: datetime,
) -> DigestReport:
    sent = _count_status(session, MessageStatus.SENT, window_start, window_end)
    failed = _count_status(session, MessageStatus.FAILED, window_start, window_end)
    pending = _count_now(session, MessageStatus.QUEUED)
    retrying = _count_now(session, MessageStatus.RETRYING)

    max_delay_s, max_id, max_why = _max_sent_delay(session, window_start, window_end)
    top_errors = _top_errors(session, window_start, window_end)
    notes: list[str] = []
    if failed:
        notes.append(f"{failed} message(s) ended in failed during the window")
    if pending + retrying > 0:
        notes.append(f"{pending + retrying} still queued/retrying at report time")
    if max_delay_s is not None and max_delay_s >= 300:
        notes.append(f"max delay ≥ 5 minutes ({max_delay_s:.0f}s)")

    return DigestReport(
        period=period,
        window_start=window_start,
        window_end=window_end,
        sent=sent,
        failed=failed,
        pending=pending,
        retrying=retrying,
        max_delay_seconds=max_delay_s,
        max_delay_message_id=max_id,
        max_delay_why=max_why,
        top_errors=tuple(top_errors),
        critical_notes=tuple(notes),
    )


def _count_status(
    session: Session,
    status: MessageStatus,
    start: datetime,
    end: datetime,
) -> int:
    n = session.scalar(
        select(func.count())
        .select_from(MessageRow)
        .where(
            MessageRow.status == status.value,
            MessageRow.updated_at >= start,
            MessageRow.updated_at < end,
        )
    )
    return int(n or 0)


def _count_now(session: Session, status: MessageStatus) -> int:
    n = session.scalar(
        select(func.count())
        .select_from(MessageRow)
        .where(MessageRow.status == status.value)
    )
    return int(n or 0)


def _max_sent_delay(
    session: Session,
    start: datetime,
    end: datetime,
) -> tuple[float | None, str | None, str | None]:
    rows = session.scalars(
        select(MessageRow)
        .where(
            MessageRow.status == MessageStatus.SENT.value,
            MessageRow.updated_at >= start,
            MessageRow.updated_at < end,
        )
        .limit(5000)
    ).all()
    best: float | None = None
    best_id: str | None = None
    best_why: str | None = None
    for row in rows:
        created = row.created_at
        updated = row.updated_at
        if created is None or updated is None:
            continue
        delay = (updated - created).total_seconds()
        if delay < 0:
            continue
        if best is None or delay > best:
            best = delay
            best_id = row.id
            best_why = (row.last_error or "delivered after queue wait").strip()[:200]
    return best, best_id, best_why


def _top_errors(session: Session, start: datetime, end: datetime, *, limit: int = 5) -> list[str]:
    rows = session.scalars(
        select(MessageRow.last_error)
        .where(
            MessageRow.status == MessageStatus.FAILED.value,
            MessageRow.updated_at >= start,
            MessageRow.updated_at < end,
            MessageRow.last_error.is_not(None),
        )
        .limit(200)
    ).all()
    counts: dict[str, int] = {}
    for err in rows:
        key = (err or "unknown").strip()[:120] or "unknown"
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [f"{n}× {msg}" for msg, n in ranked[:limit]]
