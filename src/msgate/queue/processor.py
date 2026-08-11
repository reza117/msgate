"""Process one queued message through the active mail driver."""

from __future__ import annotations

import json
from collections.abc import Callable
from email.message import EmailMessage

from sqlalchemy.orm import Session

from msgate.config.runtime import RuntimeConfig
from msgate.crypto.secrets import SecretBox
from msgate.db.models import MessageRow
from msgate.drivers.base import SendRequest, SendResult
from msgate.drivers.registry import resolve_driver
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.queue import repository as repo
from msgate.queue.backoff import backoff_seconds, is_retriable_error

log = get_logger("queue.processor")

# Test override: legacy kwargs signature from integration tests.
LegacySendFn = Callable[..., SendResult]
MAX_ATTEMPTS = 8


def process_row(
    session: Session,
    row: MessageRow,
    *,
    runtime: RuntimeConfig,
    box: SecretBox,
    send_fn: LegacySendFn | None = None,
    events: EventHub | None = None,
    already_claimed: bool = False,
) -> SendResult | None:
    """Attempt delivery; update row status. Returns SendResult on success."""
    config = runtime.get()
    driver = resolve_driver(config)
    if not driver.is_configured(config):
        repo.mark_failed(session, row, f"{driver.label()} not configured")
        return None

    if not already_claimed:
        repo.mark_processing(session, row)
    password = repo.get_password(row, box)
    mime_bytes = repo.get_mime_bytes(row)
    recipients = json.loads(row.recipients)
    request = SendRequest(
        auth_username=row.ews_username or "",
        password=password,
        mail_from=row.sender,
        rcpt_tos=recipients,
        mime_bytes=mime_bytes,
        default_sender=config.default_sender,
    )

    try:
        if send_fn is not None:
            result = send_fn(
                ews_username=request.auth_username,
                password=request.password,
                cfg=config.ews,
                mail_from=request.mail_from,
                rcpt_tos=request.rcpt_tos,
                mime_bytes=request.mime_bytes,
                default_sender=request.default_sender,
            )
        else:
            result = driver.send(request, config)
        repo.mark_sent(session, row)
        log.info(
            "queue sent id=%s backend=%s attempts=%s",
            row.id,
            driver.backend.value,
            row.attempts,
        )
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
