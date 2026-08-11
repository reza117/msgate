"""Message queue persistence."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from msgate.crypto.secrets import SecretBox
from msgate.db.models import MessageRow
from msgate.schemas.enums import MessageStatus
from msgate.schemas.messages import MessageRecord


def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


def row_to_record(row: MessageRow) -> MessageRecord:
    recipients = json.loads(row.recipients)
    return MessageRecord(
        id=row.id,
        client_ip=row.client_ip,
        raw_auth_user=row.raw_auth_user,
        sanitized_user=row.sanitized_user,
        sender=row.sender,
        recipients=recipients,
        subject=row.subject,
        status=MessageStatus(row.status),
        attempts=row.attempts,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def insert_message(
    session: Session,
    *,
    client_ip: str,
    raw_auth_user: str,
    sanitized_user: str,
    sender: str,
    recipients: list[str],
    subject: str,
    mime_bytes: bytes,
    ews_username: str,
    password: str,
    box: SecretBox,
) -> MessageRow:
    now = datetime.now(UTC)
    row = MessageRow(
        id=new_message_id(),
        client_ip=client_ip,
        raw_auth_user=raw_auth_user,
        sanitized_user=sanitized_user,
        sender=sender,
        recipients=json.dumps(recipients),
        subject=subject,
        body="",
        status=MessageStatus.QUEUED.value,
        attempts=0,
        mime_payload=base64.b64encode(mime_bytes).decode("ascii"),
        ews_username=ews_username,
        ews_password_enc=box.encrypt(password),
        next_retry_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    # Avoid refresh races with concurrent claim_next workers on SQLite.
    return session.get(MessageRow, row.id) or row


def list_messages(
    session: Session,
    *,
    status: MessageStatus | None = None,
    limit: int = 100,
) -> list[MessageRow]:
    stmt = select(MessageRow).order_by(MessageRow.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(MessageRow.status == status.value)
    return list(session.scalars(stmt))


def get_message(session: Session, message_id: str) -> MessageRow | None:
    return session.get(MessageRow, message_id)


def pending_messages(session: Session, *, limit: int = 20) -> list[MessageRow]:
    now = datetime.now(UTC)
    stmt = (
        select(MessageRow)
        .where(
            MessageRow.status.in_(
                [MessageStatus.QUEUED.value, MessageStatus.RETRYING.value],
            ),
            or_(MessageRow.next_retry_at.is_(None), MessageRow.next_retry_at <= now),
        )
        .order_by(MessageRow.created_at.asc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def claim_next(session: Session) -> MessageRow | None:
    """Atomically claim one pending message (safe for multiple workers)."""
    from sqlalchemy import update

    rows = pending_messages(session, limit=1)
    if not rows:
        return None
    row = rows[0]
    now = datetime.now(UTC)
    result = session.execute(
        update(MessageRow)
        .where(
            MessageRow.id == row.id,
            MessageRow.status.in_(
                [MessageStatus.QUEUED.value, MessageStatus.RETRYING.value],
            ),
        )
        .values(
            status=MessageStatus.PROCESSING.value,
            attempts=MessageRow.attempts + 1,
            updated_at=now,
        )
    )
    session.commit()
    if int(result.rowcount or 0) != 1:
        return None
    session.refresh(row)
    return row


def count_pending(session: Session) -> int:
    from sqlalchemy import func

    stmt = select(func.count()).select_from(MessageRow).where(
        MessageRow.status.in_(
            [MessageStatus.QUEUED.value, MessageStatus.RETRYING.value],
        ),
    )
    return int(session.scalar(stmt) or 0)


def mark_processing(session: Session, row: MessageRow) -> None:
    row.status = MessageStatus.PROCESSING.value
    row.attempts += 1
    row.updated_at = datetime.now(UTC)
    session.commit()


def mark_sent(session: Session, row: MessageRow) -> None:
    row.status = MessageStatus.SENT.value
    row.last_error = None
    row.next_retry_at = None
    row.updated_at = datetime.now(UTC)
    session.commit()


def mark_retry(session: Session, row: MessageRow, error: str, delay_seconds: float) -> None:
    from datetime import timedelta

    row.status = MessageStatus.RETRYING.value
    row.last_error = error[:2000]
    row.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
    row.updated_at = datetime.now(UTC)
    session.commit()


def mark_failed(session: Session, row: MessageRow, error: str) -> None:
    row.status = MessageStatus.FAILED.value
    row.last_error = error[:2000]
    row.next_retry_at = None
    row.updated_at = datetime.now(UTC)
    session.commit()


def get_password(row: MessageRow, box: SecretBox) -> str:
    if not row.ews_password_enc:
        return ""
    return box.decrypt(row.ews_password_enc)


def get_mime_bytes(row: MessageRow) -> bytes:
    if not row.mime_payload:
        return b""
    return base64.b64decode(row.mime_payload.encode("ascii"))


SessionFactory = sessionmaker[Session]
