"""Load GatewayConfig from environment variables."""

from __future__ import annotations

import os

from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig
from msgate.schemas.enums import AuthType, BackendType


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def load_config_from_env() -> GatewayConfig:
    bind = _env("MSGATE_SMTP_BIND", "127.0.0.1") or "127.0.0.1"
    port = int(_env("MSGATE_SMTP_PORT", "1025") or "1025")
    allowed = _env("MSGATE_SMTP_ALLOWED_IPS", "127.0.0.1") or "127.0.0.1"
    allowed_ips = [p.strip() for p in allowed.split(",") if p.strip()]

    smtp = SMTPConfig(bind_address=bind, port=port, allowed_ips=allowed_ips)

    ews_url = _env("MSGATE_EWS_URL")
    ews: EWSConfig | None = None
    if ews_url:
        auth_raw = (_env("MSGATE_EWS_AUTH_TYPE", "ntlm") or "ntlm").lower()
        auth_type = AuthType.BASIC if auth_raw == "basic" else AuthType.NTLM
        trust = (_env("MSGATE_EWS_TRUST_SELF_SIGNED", "false") or "false").lower() in {
            "1",
            "true",
            "yes",
        }
        tls_mode = (_env("MSGATE_EWS_TLS_MODE", "auto") or "auto").lower()
        if tls_mode not in {"auto", "modern", "legacy"}:
            tls_mode = "auto"
        ews = EWSConfig(
            server_url=ews_url,
            auth_type=auth_type,
            domain=_env("MSGATE_EWS_DOMAIN"),
            username=_env("MSGATE_EWS_USERNAME"),
            password=_env("MSGATE_EWS_PASSWORD"),
            trust_self_signed=trust,
            ca_file=_env("MSGATE_EWS_CA_FILE"),
            tls_mode=tls_mode,
            primary_smtp=_env("MSGATE_EWS_PRIMARY_SMTP"),
        )

    failover_url = _env("MSGATE_EWS_FAILOVER_URL")
    ews_failover: EWSConfig | None = None
    if failover_url:
        ews_failover = EWSConfig(
            server_url=failover_url,
            auth_type=ews.auth_type if ews else AuthType.NTLM,
            domain=_env("MSGATE_EWS_FAILOVER_DOMAIN") or (ews.domain if ews else None),
            username=_env("MSGATE_EWS_FAILOVER_USERNAME") or (ews.username if ews else None),
            password=_env("MSGATE_EWS_FAILOVER_PASSWORD") or (ews.password if ews else None),
            trust_self_signed=trust if ews else False,
            ca_file=_env("MSGATE_EWS_FAILOVER_CA_FILE") or (ews.ca_file if ews else None),
            tls_mode=tls_mode if ews else "auto",
            primary_smtp=_env("MSGATE_EWS_FAILOVER_PRIMARY_SMTP")
            or (ews.primary_smtp if ews else None),
        )

    return GatewayConfig(
        backend=BackendType.EWS,
        smtp=smtp,
        ews=ews,
        ews_failover=ews_failover,
        default_sender=_env("MSGATE_DEFAULT_SENDER"),
    )
