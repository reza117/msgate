"""Send capacity alerts to admin email via the configured mail driver."""

from __future__ import annotations

from email.message import EmailMessage

from msgate.app.state import AppState
from msgate.drivers.base import SendRequest
from msgate.drivers.registry import resolve_driver
from msgate.logging_setup import get_logger
from msgate.ops.capacity import CapacityStatus

log = get_logger("ops.alert_mail")


def send_capacity_alert(state: AppState, status: CapacityStatus, to_email: str) -> bool:
    cfg = state.runtime.get()
    driver = resolve_driver(cfg)
    if not driver.is_configured(cfg):
        log.warning("capacity alert skipped — mail backend not configured")
        return False
    ews = cfg.ews
    if ews is None or not ews.username or not ews.password:
        log.warning("capacity alert skipped — EWS service credentials missing")
        return False

    subject = f"[msgate] {status.level.upper()} capacity — queue {status.pending}"
    lines = [
        f"Level: {status.level}",
        f"Pending: {status.pending}",
        f"Oldest age (s): {status.oldest_age_seconds}",
        f"Circuit open: {status.circuit_open}",
        "",
        "Reasons:",
        *[f"- {r}" for r in status.reasons],
        "",
        status.hint,
    ]
    body = "\n".join(lines)
    msg = EmailMessage()
    sender = ews.primary_smtp or cfg.default_sender or ews.username
    msg["From"] = str(sender)
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    request = SendRequest(
        auth_username=ews.username,
        password=ews.password,
        mail_from=str(sender),
        rcpt_tos=[to_email],
        mime_bytes=msg.as_bytes(),
        default_sender=cfg.default_sender,
    )
    try:
        driver.send(request, cfg)
        log.info("capacity alert emailed to=%s level=%s", to_email, status.level)
        return True
    except Exception:
        log.exception("capacity alert send failed to=%s", to_email)
        return False
