"""Build ssl.SSLContext from a TLS profile + trust settings."""

from __future__ import annotations

import ssl
from pathlib import Path

from msgate.tls.profiles import TlsProfile, TlsProfileId

_TLS_VERSION = {
    "TLSv1": ssl.TLSVersion.TLSv1,
    "TLSv1_1": ssl.TLSVersion.TLSv1_1,
    "TLSv1_2": ssl.TLSVersion.TLSv1_2,
    "TLSv1_3": ssl.TLSVersion.TLSv1_3,
}


def build_ssl_context(
    profile: TlsProfile,
    *,
    ca_file: str | None = None,
    trust_self_signed: bool = False,
) -> ssl.SSLContext:
    """Create a client SSLContext for probe and requests adapters."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    if profile.min_tls:
        ctx.minimum_version = _TLS_VERSION[profile.min_tls]
    if profile.max_tls:
        ctx.maximum_version = _TLS_VERSION[profile.max_tls]

    if profile.ciphers:
        ctx.set_ciphers(profile.ciphers)

    if profile.legacy_connect:
        # OpenSSL 3: allow renegotiation / older server behavior when enabled.
        legacy = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
        if legacy:
            ctx.options |= legacy

    if trust_self_signed:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    elif ca_file:
        path = Path(ca_file)
        if not path.is_file():
            raise FileNotFoundError(f"CA file not found: {ca_file}")
        ctx.load_verify_locations(cafile=str(path))
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = True
    else:
        ctx.load_default_certs()
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = True

    return ctx


def profile_by_id(profile_id: TlsProfileId | str) -> TlsProfile:
    from msgate.tls.profiles import PROFILES

    return PROFILES[TlsProfileId(profile_id)]
