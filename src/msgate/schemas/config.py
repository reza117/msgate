"""Gateway configuration models (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from msgate.schemas.enums import AuthType, BackendType


def _empty_str_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


class EWSConfig(BaseModel):
    server_url: HttpUrl = Field(
        ...,
        examples=["https://mail.example.com/EWS/Exchange.asmx"],
    )
    auth_type: AuthType = Field(default=AuthType.NTLM, description="Authentication scheme")
    domain: str | None = Field(
        default=None,
        examples=["DOMAIN"],
        description="Default Windows Domain (example only in API docs)",
    )
    username: str | None = Field(
        default=None,
        description="EWS username (DOMAIN\\user or user@example.com)",
        examples=["DOMAIN\\svc.msgate"],
    )
    password: str | None = Field(
        default=None,
        description="EWS password (redacted as *** on GET)",
        examples=["***"],
    )
    trust_self_signed: bool = Field(default=False, description="Bypass SSL verification")
    ca_file: str | None = Field(
        default=None,
        description="Path to PEM CA bundle (preferred over trust_self_signed)",
        examples=["/etc/ssl/certs/exchange-ca.pem"],
    )
    tls_mode: str = Field(
        default="auto",
        description="TLS policy: auto | modern | legacy",
        examples=["auto"],
    )
    primary_smtp: str | None = Field(
        default=None,
        description="Mailbox primary SMTP for EWS when AUTH is DOMAIN\\user",
        examples=["svc.msgate@example.com"],
    )

    @field_validator("domain", "username", "password", "ca_file", "primary_smtp", mode="before")
    @classmethod
    def blank_optional_to_none(cls, value: object) -> object:
        return _empty_str_to_none(value)


class GraphConfig(BaseModel):
    tenant_id: str = Field(..., examples=["00000000-0000-0000-0000-000000000000"])
    client_id: str = Field(..., examples=["11111111-1111-1111-1111-111111111111"])
    client_secret: str = Field(..., description="Application secret value")
    scopes: list[str] = Field(default_factory=lambda: ["https://graph.microsoft.com/.default"])


class SMTPConfig(BaseModel):
    bind_address: str = Field(default="127.0.0.1", examples=["0.0.0.0"])
    port: int = Field(default=1025, ge=1, le=65535)
    max_message_size_mb: int = Field(default=25, ge=1, le=100)
    allowed_ips: list[str] = Field(
        default_factory=lambda: ["127.0.0.1"],
        description="Whitelisted CIDR ranges for relaying",
    )


class GatewayConfig(BaseModel):
    backend: BackendType = Field(default=BackendType.EWS)
    smtp: SMTPConfig = Field(default_factory=SMTPConfig)
    ews: EWSConfig | None = None
    ews_failover: EWSConfig | None = Field(
        default=None,
        description="Secondary Exchange endpoint when primary send fails",
    )
    graph: GraphConfig | None = None
    default_sender: EmailStr | None = Field(default=None, examples=["gateway@example.com"])

    @field_validator("default_sender", mode="before")
    @classmethod
    def blank_sender_to_none(cls, value: object) -> object:
        return _empty_str_to_none(value)

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "examples": [
                {
                    "backend": "ews",
                    "smtp": {
                        "bind_address": "127.0.0.1",
                        "port": 1025,
                        "max_message_size_mb": 25,
                        "allowed_ips": ["127.0.0.1"],
                    },
                    "ews": {
                        "server_url": "https://mail.example.com/EWS/Exchange.asmx",
                        "auth_type": "ntlm",
                        "domain": "DOMAIN",
                        "username": "DOMAIN\\svc.msgate",
                        "password": "***",
                        "trust_self_signed": False,
                        "ca_file": None,
                        "tls_mode": "auto",
                        "primary_smtp": "svc.msgate@example.com",
                    },
                    "ews_failover": None,
                    "graph": None,
                    "default_sender": "gateway@example.com",
                }
            ]
        },
    )
