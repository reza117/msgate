"""Exchange Web Services driver."""

from __future__ import annotations

from msgate.drivers.base import HealthResult, MailDriver, SendRequest, SendResult
from msgate.ews.client import build_account, send_mime
from msgate.logging_setup import get_logger
from msgate.schemas.config import EWSConfig, GatewayConfig
from msgate.schemas.enums import BackendType
from msgate.tls.negotiate import negotiate

log = get_logger("drivers.ews")


class EwsDriver(MailDriver):
    @property
    def backend(self) -> BackendType:
        return BackendType.EWS

    def is_configured(self, config: GatewayConfig) -> bool:
        return config.ews is not None

    def send(self, request: SendRequest, config: GatewayConfig) -> SendResult:
        ews = _require_ews(config)
        try:
            return _send_via(ews, request, config.default_sender)
        except Exception as primary_exc:
            failover = config.ews_failover
            if failover is None:
                raise
            log.warning("EWS primary failed; trying failover: %s", primary_exc)
            result = _send_via(failover, request, config.default_sender)
            result.driver = f"{self.backend.value}+failover"
            return result

    def health(self, config: GatewayConfig) -> HealthResult:
        ews = config.ews
        if ews is None:
            return HealthResult(ok=False, driver=self.backend.value, error="EWS not configured")
        if not ews.username or not ews.password:
            return HealthResult(
                ok=False,
                driver=self.backend.value,
                error="EWS username/password required",
            )
        return _check_ews(ews, username=ews.username, password=ews.password)


def _require_ews(config: GatewayConfig) -> EWSConfig:
    if config.ews is None:
        raise ValueError("EWS not configured")
    return config.ews


def _send_via(cfg: EWSConfig, request: SendRequest, default_sender: str | None) -> SendResult:
    result = send_mime(
        ews_username=request.auth_username,
        password=request.password,
        cfg=cfg,
        mail_from=request.mail_from,
        rcpt_tos=request.rcpt_tos,
        mime_bytes=request.mime_bytes,
        default_sender=default_sender,
    )
    return SendResult(
        message_id=result.message_id,
        changekey=result.changekey,
        driver=BackendType.EWS.value,
    )


def _check_ews(cfg: EWSConfig, *, username: str, password: str) -> HealthResult:
    import time

    try:
        t0 = time.perf_counter()
        negotiated = negotiate(cfg)
        account = build_account(username, password, cfg, mail_from=username)
        inbox = account.root / "Top of Information Store" / "Inbox"
        count = inbox.total_count
        latency = (time.perf_counter() - t0) * 1000
        return HealthResult(
            ok=True,
            latency_ms=latency,
            driver=BackendType.EWS.value,
            detail=f"Inbox accessible ({count} items)",
            extra={"tls_profile": negotiated.profile_id.value},
        )
    except Exception as exc:
        return HealthResult(ok=False, driver=BackendType.EWS.value, error=str(exc))
