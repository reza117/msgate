"""Gateway configuration models (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from msgate.schemas.enums import AuthType, BackendType


class EWSConfig(BaseModel):
    server_url: HttpUrl = Field(
        ...,
        examples=["https://exchange.domain.com/EWS/Exchange.asmx"],
    )
    auth_type: AuthType = Field(default=AuthType.NTLM, description="Authentication scheme")
    domain: str | None = Field(default=None, examples=["WDC"], description="Default Windows Domain")
    username: str | None = Field(default=None, description="EWS username")
    password: str | None = Field(default=None, description="EWS password")
    trust_self_signed: bool = Field(default=False, description="Bypass SSL verification")
    ca_file: str | None = Field(
        default=None,
        description="Path to PEM CA bundle (preferred over trust_self_signed)",
    )
    tls_mode: str = Field(
        default="auto",
        description="TLS policy: auto | modern | legacy",
        examples=["auto"],
    )
    primary_smtp: str | None = Field(
        default=None,
        description="Mailbox primary SMTP for EWS when AUTH is DOMAIN\\user",
        examples=["user@domain.com"],
    )


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
    graph: GraphConfig | None = None
    default_sender: EmailStr | None = Field(default=None, examples=["gateway@domain.com"])

    model_config = ConfigDict(use_enum_values=True)
