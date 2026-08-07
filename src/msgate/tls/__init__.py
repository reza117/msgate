"""TLS negotiation package for universal HTTPS backends."""

from msgate.tls.negotiate import (
    NegotiatedTls,
    invalidate_ews_tls,
    is_tls_failure,
    prepare_ews_tls,
)
from msgate.tls.profiles import TlsMode, TlsProfileId

__all__ = [
    "NegotiatedTls",
    "TlsMode",
    "TlsProfileId",
    "invalidate_ews_tls",
    "is_tls_failure",
    "prepare_ews_tls",
]
