"""High-level queue accept + dispatch for SMTP and API."""

from __future__ import annotations

from dataclasses import dataclass
from email import message_from_bytes

from sqlalchemy.orm import Session

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.queue import repository as repo
from msgate.queue.processor import LegacySendFn, process_row
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
    ) -> None:
        self._session_factory = session_factory
        self._runtime = runtime
        self._box = box
        self._send_fn = send_fn
        self._events = events

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
            result = process_row(
                session,
                row,
                runtime=self._runtime,
                box=self._box,
                send_fn=self._send_fn,
                events=self._events,
            )
            session.refresh(row)
            delivered = result is not None
            log.info(
                "accept id=%s status=%s delivered=%s",
                row.id,
                row.status,
                delivered,
            )
            if self._events:
                self._events.publish_sync(
                    "smtp.data",
                    f"SMTP accepted {row.id} → {row.status}",
                    message_id=row.id,
                    mail_from=mail_from,
                    subject=subject,
                )
            return AcceptResult(message_id=row.id, status=row.status, delivered=delivered)

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
