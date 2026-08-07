"""Smart Auth Sanitizer for SMTP usernames."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SanitizedAuth:
    """Normalized credentials derived from raw SMTP AUTH identity."""

    raw: str
    username: str
    domain: str | None
    ews_username: str


def sanitize_username(raw: str, default_domain: str | None = None) -> SanitizedAuth:
    """Normalize DOMAIN\\user, user@domain, or plain user for Exchange.

    Rules:
    - ``DOMAIN\\\\user`` / ``DOMAIN/user`` → username=user, domain=DOMAIN,
      ews_username=``DOMAIN\\\\user``
    - ``user@domain`` → keep UPN as ews_username (common for EWS/Basic)
    - plain ``user`` → attach default_domain when provided
    """
    value = (raw or "").strip()
    if not value:
        raise ValueError("empty username")

    # Down-level logon: DOMAIN\user or DOMAIN/user
    for sep in ("\\", "/"):
        if sep in value and "@" not in value:
            domain, _, user = value.partition(sep)
            domain = domain.strip()
            user = user.strip()
            if domain and user and "\\" not in user and "/" not in user:
                return SanitizedAuth(
                    raw=raw,
                    username=user,
                    domain=domain,
                    ews_username=f"{domain}\\{user}",
                )

    # UPN: user@domain
    if "@" in value:
        user, _, domain = value.partition("@")
        user = user.strip()
        domain = domain.strip()
        if not user or not domain:
            raise ValueError(f"invalid UPN username: {raw!r}")
        return SanitizedAuth(
            raw=raw,
            username=user,
            domain=domain,
            ews_username=value,
        )

    # Plain username
    user = value
    if default_domain:
        return SanitizedAuth(
            raw=raw,
            username=user,
            domain=default_domain,
            ews_username=f"{default_domain}\\{user}",
        )
    return SanitizedAuth(raw=raw, username=user, domain=None, ews_username=user)
