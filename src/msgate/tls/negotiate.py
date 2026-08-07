"""Negotiate, cache, and apply TLS profiles for HTTPS backends."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from exchangelib.protocol import BaseProtocol

from msgate.logging_setup import get_logger
from msgate.schemas.config import EWSConfig
from msgate.tls.adapter import make_http_adapter_class
from msgate.tls.cache import cache_key, get_cached, invalidate, put_cached
from msgate.tls.context import build_ssl_context, profile_by_id
from msgate.tls.probe import ProbeResult, probe_profile
from msgate.tls.profiles import TlsMode, TlsProfileId, ladder_for_mode

log = get_logger("tls.negotiate")


@dataclass(frozen=True, slots=True)
class NegotiatedTls:
    host: str
    port: int
    profile_id: TlsProfileId
    from_cache: bool
    probe: ProbeResult | None = None


def endpoint_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError(f"cannot parse host from URL: {url}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


def _trust_args(cfg: EWSConfig) -> tuple[str | None, bool]:
    return cfg.ca_file, cfg.trust_self_signed


def negotiate(
    cfg: EWSConfig,
    *,
    force_reprobe: bool = False,
    timeout: float = 10.0,
) -> NegotiatedTls:
    """Select a working TLS profile for the EWS endpoint."""
    host, port = endpoint_from_url(str(cfg.server_url))
    mode = TlsMode(cfg.tls_mode)
    ca_file, insecure = _trust_args(cfg)
    key = cache_key(
        host,
        port,
        tls_mode=mode.value,
        ca_file=ca_file,
        trust_self_signed=insecure,
    )

    if not force_reprobe:
        cached = get_cached(key)
        if cached is not None:
            log.info(
                "TLS using cached profile host=%s:%s profile=%s",
                host,
                port,
                cached.value,
            )
            return NegotiatedTls(
                host=host,
                port=port,
                profile_id=cached,
                from_cache=True,
            )

    last_error: str | None = None
    for profile_id in ladder_for_mode(mode):
        result = probe_profile(
            host,
            port,
            profile_id,
            ca_file=ca_file,
            trust_self_signed=insecure,
            timeout=timeout,
        )
        if result.ok:
            put_cached(key, profile_id)
            return NegotiatedTls(
                host=host,
                port=port,
                profile_id=profile_id,
                from_cache=False,
                probe=result,
            )
        last_error = result.error

    raise ConnectionError(
        f"no working TLS profile for {host}:{port} (mode={mode.value}): {last_error}"
    )


def apply_negotiated(cfg: EWSConfig, negotiated: NegotiatedTls) -> None:
    """Install exchangelib HTTP adapter for the negotiated profile."""
    profile = profile_by_id(negotiated.profile_id)
    ca_file, insecure = _trust_args(cfg)
    ctx = build_ssl_context(profile, ca_file=ca_file, trust_self_signed=insecure)
    BaseProtocol.HTTP_ADAPTER_CLS = make_http_adapter_class(ctx)
    if insecure:
        log.warning(
            "TLS verify disabled (trust_self_signed=true) profile=%s host=%s:%s",
            negotiated.profile_id.value,
            negotiated.host,
            negotiated.port,
        )
    else:
        log.info(
            "TLS adapter applied profile=%s host=%s:%s ca_file=%s",
            negotiated.profile_id.value,
            negotiated.host,
            negotiated.port,
            ca_file or "(system)",
        )


def prepare_ews_tls(cfg: EWSConfig, *, force_reprobe: bool = False) -> NegotiatedTls:
    negotiated = negotiate(cfg, force_reprobe=force_reprobe)
    apply_negotiated(cfg, negotiated)
    return negotiated


def invalidate_ews_tls(cfg: EWSConfig) -> None:
    host, port = endpoint_from_url(str(cfg.server_url))
    mode = TlsMode(cfg.tls_mode)
    ca_file, insecure = _trust_args(cfg)
    key = cache_key(
        host,
        port,
        tls_mode=mode.value,
        ca_file=ca_file,
        trust_self_signed=insecure,
    )
    invalidate(key)


def is_tls_failure(exc: BaseException) -> bool:
    """Heuristic: should we invalidate cache and re-negotiate?"""
    import ssl

    if isinstance(exc, ssl.SSLError):
        return True
    text = str(exc).lower()
    markers = (
        "ssl",
        "tls",
        "unsupported protocol",
        "certificate",
        "handshake",
        "wrong version number",
    )
    return any(m in text for m in markers)
