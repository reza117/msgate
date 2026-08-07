"""TLS profile and ladder unit tests."""

from msgate.tls.profiles import TlsMode, TlsProfileId, ladder_for_mode


def test_auto_ladder_modern_first() -> None:
    assert ladder_for_mode(TlsMode.AUTO)[0] == TlsProfileId.MODERN
    assert TlsProfileId.LEGACY_TLS1 in ladder_for_mode(TlsMode.AUTO)


def test_modern_only() -> None:
    assert ladder_for_mode(TlsMode.MODERN) == [TlsProfileId.MODERN]


def test_legacy_skips_modern() -> None:
    assert TlsProfileId.MODERN not in ladder_for_mode(TlsMode.LEGACY)
