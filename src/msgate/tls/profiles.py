"""TLS profile definitions for outbound HTTPS (EWS and future backends)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TlsMode(StrEnum):
    """Operator-selected negotiation policy."""

    AUTO = "auto"
    MODERN = "modern"
    LEGACY = "legacy"


class TlsProfileId(StrEnum):
    """Concrete client TLS profile (what was probed / cached)."""

    MODERN = "modern"
    LEGACY_TLS1_1 = "legacy_tls1_1"
    LEGACY_TLS1 = "legacy_tls1"


@dataclass(frozen=True, slots=True)
class TlsProfile:
    id: TlsProfileId
    label: str
    # None = use OpenSSL defaults for that bound
    min_tls: str | None
    max_tls: str | None
    ciphers: str | None
    legacy_connect: bool = False


PROFILES: dict[TlsProfileId, TlsProfile] = {
    TlsProfileId.MODERN: TlsProfile(
        id=TlsProfileId.MODERN,
        label="TLS 1.2+ (modern)",
        min_tls="TLSv1_2",
        max_tls=None,
        ciphers=None,
        legacy_connect=False,
    ),
    TlsProfileId.LEGACY_TLS1_1: TlsProfile(
        id=TlsProfileId.LEGACY_TLS1_1,
        label="TLS 1.1 (legacy)",
        min_tls="TLSv1_1",
        max_tls="TLSv1_1",
        ciphers="DEFAULT:@SECLEVEL=0",
        legacy_connect=True,
    ),
    TlsProfileId.LEGACY_TLS1: TlsProfile(
        id=TlsProfileId.LEGACY_TLS1,
        label="TLS 1.0 (legacy)",
        min_tls="TLSv1",
        max_tls="TLSv1",
        ciphers="DEFAULT:@SECLEVEL=0",
        legacy_connect=True,
    ),
}


def ladder_for_mode(mode: TlsMode) -> list[TlsProfileId]:
    """Ordered profiles to try for a given mode."""
    if mode == TlsMode.MODERN:
        return [TlsProfileId.MODERN]
    if mode == TlsMode.LEGACY:
        return [TlsProfileId.LEGACY_TLS1_1, TlsProfileId.LEGACY_TLS1]
    # auto: modern first, then legacy ladder (production default)
    return [
        TlsProfileId.MODERN,
        TlsProfileId.LEGACY_TLS1_1,
        TlsProfileId.LEGACY_TLS1,
    ]
