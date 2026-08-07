"""IP allowlist unit tests."""

from msgate.smtp.access import ip_allowed


def test_exact_ip() -> None:
    assert ip_allowed("127.0.0.1", ["127.0.0.1"])


def test_cidr() -> None:
    assert ip_allowed("10.0.0.5", ["10.0.0.0/24"])
    assert not ip_allowed("10.0.1.5", ["10.0.0.0/24"])


def test_deny_unknown() -> None:
    assert not ip_allowed("8.8.8.8", ["127.0.0.1"])
