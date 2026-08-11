"""aiosmtpd handler: SMTP → queue with backpressure."""

from __future__ import annotations

from msgate.config.runtime import RuntimeConfig
from msgate.logging_setup import get_logger
from msgate.queue.circuit_breaker import CircuitBreaker
from msgate.queue.service import QueueService
from msgate.smtp.access import ip_allowed
from msgate.smtp.authenticator import SmtpAuthenticator

log = get_logger("smtp.handler")


class MsgateHandler:
    def __init__(
        self,
        runtime: RuntimeConfig,
        authenticator: SmtpAuthenticator,
        queue: QueueService,
        *,
        circuit: CircuitBreaker | None = None,
    ) -> None:
        self.runtime = runtime
        self.authenticator = authenticator
        self.queue = queue
        self.circuit = circuit

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        config = self.runtime.get()
        peer_ip = session.peer[0] if session.peer else ""
        auth = self.authenticator.get(peer_ip)
        allowed = ip_allowed(peer_ip, config.smtp.allowed_ips)

        if auth is None and not allowed:
            log.warning("relay denied peer=%s (no AUTH, IP not allowlisted)", peer_ip)
            return "550 relay not permitted: AUTH required or IP allowlisted"

        ews = config.ews
        if ews is None:
            log.error("EWS config missing")
            return "451 temporary failure: EWS not configured"

        deferred = self.queue.check_backpressure(circuit=self.circuit)
        if deferred is not None:
            log.warning("SMTP defer peer=%s reason=%s", peer_ip, deferred)
            return deferred

        if auth is not None:
            ews_user = auth.sanitized.ews_username
            password = auth.password
            raw_user = auth.sanitized.raw
            sanitized_user = auth.sanitized.username
        else:
            if not ews.username or not ews.password:
                log.error("anonymous relay needs ews.username/password peer=%s", peer_ip)
                return "451 temporary failure: EWS credentials not configured"
            ews_user = ews.username
            password = ews.password
            raw_user = ""
            sanitized_user = ews.username

        mail_from = envelope.mail_from or ""
        rcpts = list(envelope.rcpt_tos)
        content = envelope.content or b""
        if isinstance(content, str):
            content = content.encode("utf-8", errors="replace")

        log.info(
            "SMTP DATA peer=%s raw_auth=%r sanitized=%r from=%s rcpts=%s bytes=%d",
            peer_ip,
            raw_user,
            sanitized_user,
            mail_from,
            rcpts,
            len(content),
        )

        try:
            result = self.queue.accept_smtp(
                client_ip=peer_ip,
                raw_auth_user=raw_user,
                sanitized_user=sanitized_user,
                mail_from=mail_from,
                rcpt_tos=rcpts,
                mime_bytes=content,
                ews_username=ews_user,
                password=password,
            )
        except Exception as exc:
            log.exception("queue accept failed peer=%s err=%s", peer_ip, exc)
            return f"451 temporary failure: {exc}"

        log.info(
            "SMTP accepted peer=%s msg_id=%s status=%s delivered=%s",
            peer_ip,
            result.message_id,
            result.status,
            result.delivered,
        )
        return "250 Message accepted for delivery"
