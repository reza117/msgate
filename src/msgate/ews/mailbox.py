"""Resolve Exchange primary SMTP address for EWS Account."""

from __future__ import annotations

from email.utils import parseaddr

from msgate.schemas.config import EWSConfig


def _looks_like_email(value: str) -> bool:
    _, addr = parseaddr(value)
    addr = (addr or value).strip()
    return "@" in addr and " " not in addr and not addr.endswith("@localhost")


def resolve_primary_smtp(
    *,
    ews_username: str,
    mail_from: str | None,
    cfg: EWSConfig,
    default_sender: str | None = None,
) -> str:
    """Pick a real mailbox SMTP address for exchangelib Account.

    Order:
    1. EWSConfig.primary_smtp (explicit operator setting)
    2. default_sender / GatewayConfig default
    3. SMTP envelope From (if email-shaped)
    4. ews_username when it is already a UPN/email
    """
    candidates = [
        cfg.primary_smtp,
        default_sender,
        mail_from,
        ews_username if "@" in (ews_username or "") else None,
        cfg.username if cfg.username and "@" in cfg.username else None,
    ]
    for raw in candidates:
        if not raw:
            continue
        _, addr = parseaddr(str(raw))
        addr = (addr or str(raw)).strip()
        if _looks_like_email(addr):
            return addr

    raise ValueError(
        "cannot resolve mailbox SMTP address for EWS; set MSGATE_EWS_PRIMARY_SMTP "
        "or MSGATE_DEFAULT_SENDER, or AUTH with user@domain, or send a valid From address"
    )
