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
        ews_username=r"WDC\internal.wdc",
        mail_from="internal.wdc@wigner.hun-ren.hu",
        cfg=_cfg(),
    )
    assert addr == "internal.wdc@wigner.hun-ren.hu"


def test_uses_explicit_primary_smtp() -> None:
    addr = resolve_primary_smtp(
        ews_username=r"WDC\internal.wdc",
        mail_from="other@example.com",
        cfg=_cfg(primary_smtp="svc@wigner.hun-ren.hu"),
    )
    assert addr == "svc@wigner.hun-ren.hu"


def test_uses_upn_username() -> None:
    addr = resolve_primary_smtp(
        ews_username="internal.wdc@wigner.hun-ren.hu",
        mail_from=None,
        cfg=_cfg(),
    )
    assert addr == "internal.wdc@wigner.hun-ren.hu"


def test_rejects_localhost_fallback() -> None:
    with pytest.raises(ValueError, match="cannot resolve mailbox SMTP"):
        resolve_primary_smtp(
            ews_username=r"WDC\internal.wdc",
            mail_from=None,
            cfg=_cfg(),
        )
