"""Mailbox SMTP address resolution tests."""

import pytest

from msgate.ews.mailbox import resolve_primary_smtp
from msgate.schemas.config import EWSConfig


def _cfg(**kwargs) -> EWSConfig:
    return EWSConfig(
        server_url="https://exchange.example.com/EWS/Exchange.asmx",
        **kwargs,
    )


def test_uses_mail_from_when_domain_user() -> None:
    addr = resolve_primary_smtp(
        ews_username=r"DOMAIN\user",
        mail_from="user@example.com",
        cfg=_cfg(),
    )
    assert addr == "user@example.com"


def test_uses_explicit_primary_smtp() -> None:
    addr = resolve_primary_smtp(
        ews_username=r"DOMAIN\user",
        mail_from="other@example.com",
        cfg=_cfg(primary_smtp="svc@example.com"),
    )
    assert addr == "svc@example.com"


def test_uses_upn_username() -> None:
    addr = resolve_primary_smtp(
        ews_username="user@example.com",
        mail_from=None,
        cfg=_cfg(),
    )
    assert addr == "user@example.com"


def test_rejects_localhost_fallback() -> None:
    with pytest.raises(ValueError, match="cannot resolve mailbox SMTP"):
        resolve_primary_smtp(
            ews_username=r"DOMAIN\user",
            mail_from=None,
            cfg=_cfg(),
        )
