"""TCP+TLS handshake probe for endpoint capability discovery."""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass

from msgate.logging_setup import get_logger
from msgate.tls.context import build_ssl_context
from msgate.tls.profiles import PROFILES, TlsProfileId

log = get_logger("tls.probe")


@dataclass(frozen=True, slots=True)
class ProbeResult:
    profile_id: TlsProfileId
    ok: bool
    error: str | None = None
    negotiated: str | None = None


def probe_profile(
    host: str,
    port: int,
    profile_id: TlsProfileId,
    *,
    ca_file: str | None = None,
    trust_self_signed: bool = False,
    timeout: float = 10.0,
) -> ProbeResult:
    profile = PROFILES[profile_id]
    try:
        ctx = build_ssl_context(
            profile,
            ca_file=ca_file,
            trust_self_signed=trust_self_signed,
        )
    except Exception as exc:
        return ProbeResult(profile_id=profile_id, ok=False, error=str(exc))

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                negotiated = tls.version()
                log.info(
                    "TLS probe ok host=%s:%s profile=%s negotiated=%s",
                    host,
                    port,
                    profile_id.value,
                    negotiated,
                )
                return ProbeResult(
                    profile_id=profile_id,
                    ok=True,
                    negotiated=negotiated,
                )
    except (OSError, ssl.SSLError) as exc:
        log.info(
            "TLS probe fail host=%s:%s profile=%s err=%s",
            host,
            port,
            profile_id.value,
            exc,
        )
        return ProbeResult(profile_id=profile_id, ok=False, error=str(exc))
