"""Email digest PDF via configured mail driver."""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage

from msgate.app.state import AppState
from msgate.drivers.base import SendRequest
from msgate.drivers.registry import resolve_driver
from msgate.logging_setup import get_logger
from msgate.ops.digest_pdf import text_pdf
from msgate.ops.digest_report import DigestReport

log = get_logger("ops.digest_mail")


@dataclass(frozen=True, slots=True)
class DigestSendResult:
    ok: bool
    error: str = ""


def send_digest(
    state: AppState,
    report: DigestReport,
    *,
    to_email: str,
    subject_template: str,
    include_body: bool = True,
) -> DigestSendResult:
    cfg = state.runtime.get()
    driver = resolve_driver(cfg)
    if not driver.is_configured(cfg):
        log.warning("digest skipped — mail backend not configured")
        return DigestSendResult(False, "Mail backend not configured (Settings → Exchange).")
    ews = cfg.ews
    if ews is None or not ews.username or not ews.password:
        log.warning("digest skipped — EWS service credentials missing")
        return DigestSendResult(
            False,
            "EWS username/password missing — open Settings → Exchange and save credentials.",
        )

    lines = report.body_lines()
    pdf = text_pdf(f"msgate {report.period} digest", lines)
    subject = report.subject(subject_template)
    sender = ews.primary_smtp or cfg.default_sender or ews.username

    msg = EmailMessage()
    msg["From"] = str(sender)
    msg["To"] = to_email
    msg["Subject"] = subject
    if include_body:
        msg.set_content("\n".join(lines) + "\n\n(See PDF attachment for the same report.)\n")
    else:
        msg.set_content("msgate digest attached as PDF.\n")
    msg.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=f"msgate-{report.period}-digest.pdf",
    )

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
        log.info(
            "digest emailed to=%s period=%s sent=%s failed=%s",
            to_email,
            report.period,
            report.sent,
            report.failed,
        )
        return DigestSendResult(True)
    except Exception as exc:
        log.exception("digest send failed to=%s", to_email)
        return DigestSendResult(False, f"EWS send failed: {exc}")
