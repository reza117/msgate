"""EWS account cache tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from msgate.ews.account_cache import cache_get, cache_invalidate, cache_put
from msgate.ews.client import build_account
from msgate.schemas.config import EWSConfig


def test_account_cache_hit_reuses_instance() -> None:
    cache_invalidate()
    cfg = EWSConfig(
        server_url="https://mail.example.com/EWS/Exchange.asmx",
        primary_smtp="svc@example.com",
    )
    fake = MagicMock(name="Account")
    with patch("msgate.ews.client.prepare_ews_tls"), patch(
        "msgate.ews.client.Credentials",
    ), patch("msgate.ews.client.Configuration"), patch(
        "msgate.ews.client.Account",
        return_value=fake,
    ) as account_cls:
        a1 = build_account(r"DOMAIN\svc", "pw", cfg, mail_from="svc@example.com")
        a2 = build_account(r"DOMAIN\svc", "pw", cfg, mail_from="svc@example.com")
        assert a1 is a2 is fake
        assert account_cls.call_count == 1


def test_cache_invalidate_by_user() -> None:
    cache_invalidate()
    key = ("ep", "user1", "pw", "a@b.c", "NTLM")
    cache_put(key, MagicMock())
    assert cache_get(key) is not None
    cache_invalidate(username="user1")
    assert cache_get(key) is None
