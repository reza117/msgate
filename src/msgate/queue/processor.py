"""Process one queued message through EWS."""

from __future__ import annotations

import json
from collections.abc import Callable
from email.message import EmailMessage

from sqlalchemy.orm import Session

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.db.models import MessageRow
from msgate.events import EventHub
from msgate.ews.client import SendResult, send_mime
from msgate.logging_setup import get_logger
from msgate.queue import repository as repo
from msgate.queue.backoff import backoff_seconds, is_retriable_error

log = get_logger("queue.processor")

SendFn = Callable[..., SendResult]
MAX_ATTEMPTS = 8


def process_row(
    session: Session,
    row: MessageRow,
    *,
    runtime: RuntimeConfig,
    box: SecretBox,
    send_fn: SendFn | None = None,
    events: EventHub | None = None,
) -> SendResult | None:
    """Attempt delivery; update row status. Returns SendResult on success."""
    config = runtime.get()
    ews = config.ews
    if ews is None:
        repo.mark_failed(session, row, "EWS not configured")
        return None

    repo.mark_processing(session, row)
    password = repo.get_password(row, box)
    mime_bytes = repo.get_mime_bytes(row)
    recipients = json.loads(row.recipients)
    sender = send_fn or send_mime

    try:
        result = sender(
            ews_username=row.ews_username or "",
            password=password,
            cfg=ews,
            mail_from=row.sender,
            rcpt_tos=recipients,
            mime_bytes=mime_bytes,
            default_sender=config.default_sender,
        )
        repo.mark_sent(session, row)
        log.info("queue sent id=%s attempts=%s", row.id, row.attempts)
        if events:
            events.publish_sync("queue.sent", f"Delivered {row.id}", id=row.id)
        return result
    except Exception as exc:
        err = str(exc)
        if is_retriable_error(exc) and row.attempts < MAX_ATTEMPTS:
            delay = backoff_seconds(row.attempts)
            repo.mark_retry(session, row, err, delay)
            log.warning(
                "queue retry id=%s attempts=%s delay=%ss err=%s",
                row.id,
                row.attempts,
                delay,
                err,
            )
            if events:
                events.publish_sync(
                    "queue.retry",
                    f"Retry {row.id} in {delay:.0f}s",
                    id=row.id,
                    error=err,
                )
        else:
            repo.mark_failed(session, row, err)
            log.error("queue failed id=%s attempts=%s err=%s", row.id, row.attempts, err)
            if events:
                events.publish_sync("queue.failed", f"Failed {row.id}", id=row.id, error=err)
        return None


def build_mime_from_test(
    sender: str,
    recipients: list[str],
    subject: str,
    body: str,
    *,
    is_html: bool = False,
) -> bytes:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    if is_html:
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)
    return msg.as_bytes()
