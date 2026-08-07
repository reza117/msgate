"""Dashboard statistics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from msgate.db.models import MessageRow
from msgate.schemas.enums import MessageStatus


class DashboardStats(BaseModel):
    sent_today: int = 0
    queue_pending: int = 0
    failed_24h: int = 0
    auth_errors_24h: int = 0
    backend_latency_ms: float = 0.0
    smtp_port: int = 1025
    ews_connected: bool = False


def compute_stats(
    session: Session,
    *,
    pending: int,
    auth_errors: int,
    backend_latency_ms: float,
    smtp_port: int,
    ews_connected: bool,
) -> DashboardStats:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_ago = datetime.now(UTC) - timedelta(hours=24)

    sent_today = session.scalar(
        select(func.count())
        .select_from(MessageRow)
        .where(
            MessageRow.status == MessageStatus.SENT.value,
            MessageRow.updated_at >= today_start,
        )
    )
    failed_24h = session.scalar(
        select(func.count())
        .select_from(MessageRow)
        .where(
            MessageRow.status == MessageStatus.FAILED.value,
            MessageRow.updated_at >= day_ago,
        )
    )
    return DashboardStats(
        sent_today=int(sent_today or 0),
        queue_pending=pending,
        failed_24h=int(failed_24h or 0),
        auth_errors_24h=auth_errors,
        backend_latency_ms=backend_latency_ms,
        smtp_port=smtp_port,
        ews_connected=ews_connected,
    )
