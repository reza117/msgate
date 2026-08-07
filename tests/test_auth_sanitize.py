"""Unit tests for Smart Auth Sanitizer."""

import pytest

from msgate.auth import sanitize_username


def test_domain_backslash() -> None:
    s = sanitize_username(r"WDC\internal.wdc")
    assert s.username == "internal.wdc"
    assert s.domain == "WDC"
    assert s.ews_username == r"WDC\internal.wdc"


def test_domain_slash() -> None:
    s = sanitize_username("WDC/internal.wdc")
    assert s.username == "internal.wdc"
    assert s.domain == "WDC"
    assert s.ews_username == r"WDC\internal.wdc"


def test_upn() -> None:
    s = sanitize_username("user@example.com")
    assert s.username == "user"
    assert s.domain == "example.com"
    assert s.ews_username == "user@example.com"


def test_plain_with_default_domain() -> None:
    s = sanitize_username("internal.wdc", default_domain="WDC")
    assert s.ews_username == r"WDC\internal.wdc"


def test_plain_without_domain() -> None:
    s = sanitize_username("internal.wdc")
    assert s.ews_username == "internal.wdc"
    assert s.domain is None


def test_empty_rejected() -> None:
    with pytest.raises(ValueError):
        sanitize_username("  ")
