"""Shared enums for msgate schemas."""

from enum import StrEnum


class BackendType(StrEnum):
    EWS = "ews"
    GRAPH = "graph"
    GMAIL = "gmail"


class AuthType(StrEnum):
    BASIC = "basic"
    NTLM = "ntlm"
    OAUTH2 = "oauth2"


class MessageStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
