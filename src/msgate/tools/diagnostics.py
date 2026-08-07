"""Auth simulator and EWS health tools."""

from __future__ import annotations

import base64
import time

from pydantic import BaseModel, Field

from msgate.auth.sanitize import sanitize_username
from msgate.ews.client import build_account
from msgate.schemas.config import EWSConfig
from msgate.tls.negotiate import negotiate


class AuthSimRequest(BaseModel):
    mechanism: str = Field(default="PLAIN", examples=["PLAIN", "LOGIN"])
    payload: str = Field(
        ...,
        description="Base64 AUTH payload or raw user for LOGIN",
        examples=["RE9NQUlOXHN2Yy5tc2dhdGU="],
    )
    password: str | None = Field(default=None, description="Required for LOGIN simulation")
    default_domain: str | None = Field(default=None, examples=["DOMAIN"])


class AuthSimResult(BaseModel):
    ok: bool = Field(..., examples=[True])
    raw_user: str = Field(default="", examples=["DOMAIN\\svc.msgate"])
    sanitized_user: str = Field(default="", examples=["svc.msgate"])
    ews_username: str = Field(default="", examples=["DOMAIN\\svc.msgate"])
    domain: str | None = Field(default=None, examples=["DOMAIN"])
    error: str | None = Field(default=None, examples=[None])


def simulate_auth(req: AuthSimRequest) -> AuthSimResult:
    mech = req.mechanism.upper()
    try:
        if mech == "PLAIN":
            raw = base64.b64decode(req.payload.strip()).decode("utf-8", errors="replace")
            # PLAIN: \0user\0pass
            parts = raw.split("\0")
            user = parts[1] if len(parts) >= 2 else parts[0]
        elif mech == "LOGIN":
            user = base64.b64decode(req.payload.strip()).decode("utf-8", errors="replace")
        else:
            return AuthSimResult(ok=False, error=f"unsupported mechanism: {mech}")

        s = sanitize_username(user, default_domain=req.default_domain)
        return AuthSimResult(
            ok=True,
            raw_user=s.raw,
            sanitized_user=s.username,
            ews_username=s.ews_username,
            domain=s.domain,
        )
    except Exception as exc:
        return AuthSimResult(ok=False, error=str(exc))


class EwsHealthResult(BaseModel):
    ok: bool = Field(..., examples=[True])
    latency_ms: float = Field(default=0.0, examples=[42.5])
    tls_profile: str | None = Field(default=None, examples=["modern"])
    detail: str = Field(default="", examples=["Inbox accessible (0 items)"])
    error: str | None = Field(default=None, examples=[None])


def check_ews_health(cfg: EWSConfig, *, username: str, password: str) -> EwsHealthResult:
    try:
        t0 = time.perf_counter()
        negotiated = negotiate(cfg)
        account = build_account(username, password, cfg, mail_from=username)
        inbox = account.root / "Top of Information Store" / "Inbox"
        _ = inbox.total_count
        latency = (time.perf_counter() - t0) * 1000
        return EwsHealthResult(
            ok=True,
            latency_ms=latency,
            tls_profile=negotiated.profile_id.value,
            detail=f"Inbox accessible ({inbox.total_count} items)",
        )
    except Exception as exc:
        return EwsHealthResult(ok=False, error=str(exc))
