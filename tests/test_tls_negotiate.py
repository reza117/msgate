"""TLS cache + negotiate unit tests (mocked probes)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from msgate.schemas.config import EWSConfig
from msgate.tls.cache import cache_key, clear_memory, get_cached, invalidate, put_cached
from msgate.tls.negotiate import is_tls_failure, negotiate
from msgate.tls.probe import ProbeResult
from msgate.tls.profiles import TlsProfileId


def test_cache_roundtrip(tmp_path: Path) -> None:
    clear_memory()
    path = tmp_path / "tls_cache.json"
    key = cache_key("ex.example", 443, tls_mode="auto", ca_file=None, trust_self_signed=True)
    put_cached(key, TlsProfileId.LEGACY_TLS1, path=path)
    clear_memory()
    assert get_cached(key, path=path) == TlsProfileId.LEGACY_TLS1
    invalidate(key, path=path)
    clear_memory()
    assert get_cached(key, path=path) is None


def test_negotiate_auto_falls_to_legacy(tmp_path: Path) -> None:
    clear_memory()
    cfg = EWSConfig(
        server_url="https://exchange.example.com/EWS/Exchange.asmx",
        tls_mode="auto",
        trust_self_signed=True,
    )

    def fake_probe(host, port, profile_id, **kwargs):
        ok = profile_id == TlsProfileId.LEGACY_TLS1
        return ProbeResult(
            profile_id=profile_id,
            ok=ok,
            error=None if ok else "fail",
            negotiated="TLSv1" if ok else None,
        )

    with (
        patch("msgate.tls.negotiate.probe_profile", side_effect=fake_probe),
        patch("msgate.tls.negotiate.put_cached") as put,
        patch("msgate.tls.negotiate.get_cached", return_value=None),
    ):
        result = negotiate(cfg, force_reprobe=True)
        assert result.profile_id == TlsProfileId.LEGACY_TLS1
        assert result.from_cache is False
        put.assert_called()


def test_is_tls_failure_detects_protocol_errors() -> None:
    assert is_tls_failure(Exception("UNSUPPORTED_PROTOCOL unsupported protocol"))
    assert not is_tls_failure(Exception("401 Unauthorized"))
