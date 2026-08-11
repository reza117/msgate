"""Capacity / overload evaluation for UI banners and alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from msgate.db.models import MessageRow
from msgate.ops.alerts_config import OpsAlertsConfig
from msgate.queue.circuit_breaker import CircuitBreaker, CircuitState
from msgate.schemas.enums import MessageStatus


@dataclass(frozen=True)
class CapacityStatus:
    level: str  # ok | warn | critical
    pending: int
    oldest_age_seconds: float | None
    circuit_open: bool
    reasons: tuple[str, ...]
    hint: str


def oldest_pending_age_seconds(session: Session) -> float | None:
    stmt = (
        select(MessageRow.created_at)
        .where(
            MessageRow.status.in_(
                [MessageStatus.QUEUED.value, MessageStatus.RETRYING.value],
            ),
        )
        .order_by(MessageRow.created_at.asc())
        .limit(1)
    )
    created = session.scalar(stmt)
    if created is None:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - created).total_seconds())


def evaluate_capacity(
    session: Session,
    *,
    pending: int,
    circuit: CircuitBreaker,
    ops: OpsAlertsConfig,
) -> CapacityStatus:
    reasons: list[str] = []
    level = "ok"
    age = oldest_pending_age_seconds(session)
    circuit_open = circuit.state == CircuitState.OPEN

    if circuit_open:
        reasons.append("Outbound circuit breaker is open (Exchange send failures)")
        level = "critical"

    if pending >= ops.queue_critical_pending:
        reasons.append(
            f"Queue depth {pending} ≥ critical threshold {ops.queue_critical_pending}",
        )
        level = "critical"
    elif pending >= ops.queue_warn_pending:
        reasons.append(
            f"Queue depth {pending} ≥ warn threshold {ops.queue_warn_pending}",
        )
        if level == "ok":
            level = "warn"

    if age is not None and age >= ops.queue_warn_age_seconds:
        reasons.append(f"Oldest queued message age {age:.0f}s")
        if level == "ok":
            level = "warn"
        if age >= ops.queue_warn_age_seconds * 3:
            level = "critical"

    hint = ""
    if level != "ok":
        hint = (
            "If this persists after the storm drains: raise MSGATE_QUEUE_WORKERS, "
            "or switch to Postgres (MSGATE_DATABASE_URL). See AI-14 docs."
        )

    return CapacityStatus(
        level=level,
        pending=pending,
        oldest_age_seconds=age,
        circuit_open=circuit_open,
        reasons=tuple(reasons),
        hint=hint,
    )
