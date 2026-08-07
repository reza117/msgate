"""EWS package exports."""

from msgate.drivers.base import SendResult
from msgate.ews.client import send_mime

__all__ = ["SendResult", "send_mime"]
