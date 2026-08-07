"""Exchange EWS outbound sender (exchangelib)."""

from __future__ import annotations

from email import message_from_bytes
from email.message import Message as EmailMessage
from email.utils import parseaddr

from exchangelib import (
    BASIC,
    DELEGATE,
    NTLM,
    Account,
    Configuration,
    Credentials,
    HTMLBody,
    Mailbox,
    Message,
)

from msgate.drivers.base import SendResult
from msgate.ews.mailbox import resolve_primary_smtp
from msgate.logging_setup import get_logger
from msgate.schemas.config import EWSConfig
from msgate.schemas.enums import AuthType
from msgate.tls import invalidate_ews_tls, is_tls_failure, prepare_ews_tls

log = get_logger("ews")


def _auth_type(cfg: EWSConfig) -> str:
    if cfg.auth_type == AuthType.BASIC:
        return BASIC
    return NTLM


def build_account(
    ews_username: str,
    password: str,
    cfg: EWSConfig,
    *,
    mail_from: str | None = None,
    default_sender: str | None = None,
) -> Account:
    if not cfg.server_url:
        raise ValueError("EWS server_url is required")

    prepare_ews_tls(cfg)
    primary = resolve_primary_smtp(
        ews_username=ews_username,
        mail_from=mail_from,
        cfg=cfg,
        default_sender=default_sender,
    )
    log.info(
        "EWS account primary_smtp=%s auth_user=%s",
        primary,
        ews_username,
    )
    credentials = Credentials(username=ews_username, password=password)
    configuration = Configuration(
        service_endpoint=str(cfg.server_url),
        credentials=credentials,
        auth_type=_auth_type(cfg),
    )

    return Account(
        primary_smtp_address=primary,
        config=configuration,
        autodiscover=False,
        access_type=DELEGATE,
    )


def _recipients_from_envelope(envelope_rcpts: list[str]) -> list[Mailbox]:
    boxes: list[Mailbox] = []
    for rcpt in envelope_rcpts:
        _, addr = parseaddr(rcpt)
        addr = addr or rcpt
        if addr:
            boxes.append(Mailbox(email_address=addr))
    return boxes


def _build_ews_message(
    *,
    account: Account,
    mail_from: str,
    rcpt_tos: list[str],
    mime_bytes: bytes,
) -> Message:
    msg: EmailMessage = message_from_bytes(mime_bytes)
    subject = msg.get("Subject", "") or ""
    _, from_addr = parseaddr(mail_from or msg.get("From", "") or "")
    body_text = ""
    body_html = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html" and body_html is None:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                body_html = payload.decode(charset, errors="replace")
            elif ctype == "text/plain" and not body_text:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            body_html = text
        else:
            body_text = text

    to_recipients = _recipients_from_envelope(rcpt_tos)
    if not to_recipients:
        raise ValueError("no recipients")

    ews_msg = Message(
        account=account,
        subject=subject,
        body=HTMLBody(body_html) if body_html is not None else body_text,
        to_recipients=to_recipients,
    )
    if from_addr:
        ews_msg.author = Mailbox(email_address=from_addr)
    return ews_msg


def send_mime(
    *,
    ews_username: str,
    password: str,
    cfg: EWSConfig,
    mail_from: str,
    rcpt_tos: list[str],
    mime_bytes: bytes,
    default_sender: str | None = None,
) -> SendResult:
    """Parse MIME and send via EWS, with one TLS re-negotiate on SSL failure."""

    def _attempt(*, force_reprobe: bool) -> SendResult:
        if force_reprobe:
            invalidate_ews_tls(cfg)
            prepare_ews_tls(cfg, force_reprobe=True)
        account = build_account(
            ews_username,
            password,
            cfg,
            mail_from=mail_from,
            default_sender=default_sender,
        )
        ews_msg = _build_ews_message(
            account=account,
            mail_from=mail_from,
            rcpt_tos=rcpt_tos,
            mime_bytes=mime_bytes,
        )
        log.info(
            "EWS send start user=%s from=%s recipients=%s subject=%r",
            ews_username,
            mail_from,
            rcpt_tos,
            ews_msg.subject,
        )
        ews_msg.send_and_save()
        log.info("EWS send ok id=%s", getattr(ews_msg, "id", None))
        return SendResult(
            message_id=getattr(ews_msg, "id", None),
            changekey=getattr(ews_msg, "changekey", None),
        )

    try:
        return _attempt(force_reprobe=False)
    except Exception as exc:
        if not is_tls_failure(exc):
            raise
        log.warning("EWS TLS failure; invalidating cache and re-probing: %s", exc)
        return _attempt(force_reprobe=True)
