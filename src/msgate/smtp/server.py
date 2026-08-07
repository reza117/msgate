"""SMTP server controller."""

from __future__ import annotations

from aiosmtpd.controller import Controller

from msgate.config.runtime import RuntimeConfig
from msgate.events import EventHub
from msgate.logging_setup import get_logger
from msgate.queue.service import QueueService
from msgate.smtp.authenticator import SmtpAuthenticator
from msgate.smtp.handler import MsgateHandler

log = get_logger("smtp.server")


def create_controller(
    runtime: RuntimeConfig,
    queue: QueueService,
    *,
    events: EventHub | None = None,
) -> tuple[Controller, SmtpAuthenticator]:
    config = runtime.get()
    domain = config.ews.domain if config.ews else None
    authenticator = SmtpAuthenticator(default_domain=domain, events=events)
    handler = MsgateHandler(runtime=runtime, authenticator=authenticator, queue=queue)

    controller = Controller(
        handler,
        hostname=config.smtp.bind_address,
        port=config.smtp.port,
        authenticator=authenticator,
        auth_required=False,
        auth_require_tls=False,
        decode_data=False,
    )
    log.info(
        "SMTP controller ready bind=%s port=%s allowed_ips=%s",
        config.smtp.bind_address,
        config.smtp.port,
        config.smtp.allowed_ips,
    )
    return controller, authenticator
