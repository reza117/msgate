"""Pluggable outbound mail drivers."""

from msgate.drivers.base import HealthResult, MailDriver, SendRequest, SendResult
from msgate.drivers.registry import check_backend_health, get_driver

__all__ = [
    "HealthResult",
    "MailDriver",
    "SendRequest",
    "SendResult",
    "check_backend_health",
    "get_driver",
]
