"""High-level queue accept + dispatch for SMTP and API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from email import message_from_bytes

from sqlalchemy.orm import Session

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.observability.metrics import MetricsRegistry
from msgate.queue import repository as repo
from msgate.queue.circuit_breaker import CircuitBreaker, CircuitState, queue_max_pending
from msgate.queue.processor import LegacySendFn
from msgate.schemas.enums import MessageStatus
from msgate.schemas.messages import MessageRecord

log = get_logger("queue.service")


@dataclass(slots=True)
class AcceptResult:
    message_id: str
    status: str
    delivered: bool


class QueueService:
    def __init__(
        self,
        session_factory: repo.SessionFactory,
        runtime: RuntimeConfig,
        box: SecretBox,
        *,
        send_fn: LegacySendFn | None = None,
        events: EventHub | None = None,
        wake: Callable[[], None] | None = None,
        metrics: MetricsRegistry | None = None,
        max_pending: int | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._box = box
        self._send_fn = send_fn
        self._events = events
        self._wake = wake
        self._metrics = metrics
        self._max_pending = max_pending if max_pending is not None else queue_max_pending()

    def check_backpressure(self, *, circuit: CircuitBreaker | None = None) -> str | None:
        """Return SMTP 4xx response text if accept should be deferred, else None."""
        import os

        reject_circuit = os.environ.get(
            "MSGATE_SMTP_REJECT_ON_CIRCUIT",
            "true",
        ).strip().lower() in {"1", "true", "yes", "on"}

        if circuit is not None and reject_circuit and circuit.state == CircuitState.OPEN:
            if self._metrics:
                self._metrics.inc_smtp_deferred()
            return "451 temporary failure: outbound circuit open — try later"

        with self._session_factory() as session:
            pending = repo.count_pending(session)
        if pending >= self._max_pending:
            if self._metrics:
                self._metrics.inc_smtp_deferred()
            return (
                f"452 insufficient storage: queue full "
                f"({pending}/{self._max_pending}) — try later"
            )
        return None

    def accept_smtp(
        self,
        *,
        client_ip: str,
        raw_auth_user: str,
        sanitized_user: str,
        mail_from: str,
        rcpt_tos: list[str],
        mime_bytes: bytes,
        ews_username: str,
        password: str,
    ) -> AcceptResult:
        """Fast-accept: persist to queue only; workers deliver asynchronously."""
        msg = message_from_bytes(mime_bytes)
        subject = msg.get("Subject", "") or ""

        with self._session_factory() as session:
            row = repo.insert_message(
                session,
                client_ip=client_ip,
                raw_auth_user=raw_auth_user,
                sanitized_user=sanitized_user,
                sender=mail_from,
                recipients=rcpt_tos,
                subject=subject,
                mime_bytes=mime_bytes,
                ews_username=ews_username,
                password=password,
                box=self._box,
            )
            log.info("accept id=%s status=%s (queued)", row.id, row.status)
            if self._events:
                self._events.publish_sync(
                    "smtp.data",
                    f"SMTP accepted {row.id} → {MessageStatus.QUEUED.value}",
                    message_id=row.id,
                    mail_from=mail_from,
                    subject=subject,
                )
            result = AcceptResult(
                message_id=row.id,
                status=row.status,
                delivered=False,
            )

        if self._wake:
            self._wake()
        return result

    def submit_test(
        self,
        *,
        sender: str,
        recipients: list[str],
        subject: str,
        body: str,
        is_html: bool,
        ews_username: str,
        password: str,
    ) -> AcceptResult:
        from msgate.queue.processor import build_mime_from_test

        mime = build_mime_from_test(
            sender,
            recipients,
            subject,
            body,
            is_html=is_html,
        )
        return self.accept_smtp(
            client_ip="api",
            raw_auth_user=ews_username,
            sanitized_user=ews_username,
            mail_from=sender,
            rcpt_tos=recipients,
            mime_bytes=mime,
            ews_username=ews_username,
            password=password,
        )

    def list_queue(
        self,
        session: Session,
        *,
        status=None,
        limit: int = 100,
    ) -> list[MessageRecord]:
        rows = repo.list_messages(session, status=status, limit=limit)
        return [repo.row_to_record(r) for r in rows]

    def pending_count(self, session: Session) -> int:
        return repo.count_pending(session)
