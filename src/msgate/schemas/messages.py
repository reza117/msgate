"""Message request and queue record models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from msgate.schemas.enums import MessageStatus


class EmailMessageRequest(BaseModel):
    sender: EmailStr = Field(..., examples=["alerts@example.com"])
    recipients: list[EmailStr] = Field(..., examples=[["ops@example.com"]])
    subject: str = Field(..., examples=["[PROBLEM] High CPU utilization"])
    body: str = Field(..., examples=["CPU load exceeded 95% on host-01"])
    is_html: bool = False


class MessageRecord(BaseModel):
    """Queued or historical message summary (OpenAPI examples are fictional)."""

    id: str = Field(..., examples=["msg_01hxyzexample"])
    client_ip: str = Field(..., examples=["127.0.0.1"])
    raw_auth_user: str = Field(
        ...,
        description="SMTP AUTH username as received (may include DOMAIN\\user)",
        examples=["DOMAIN\\svc.msgate"],
    )
    sanitized_user: str = Field(
        ...,
        description="Username after Smart Auth Sanitizer",
        examples=["svc.msgate"],
    )
    sender: EmailStr = Field(..., examples=["alerts@example.com"])
    recipients: list[EmailStr] = Field(..., examples=[["ops@example.com"]])
    subject: str = Field(..., examples=["Test message"])
    status: MessageStatus = Field(..., examples=["queued"])
    attempts: int = Field(default=0, examples=[0])
    last_error: str | None = Field(default=None, examples=[None])
    created_at: datetime = Field(..., examples=["2026-01-15T12:00:00Z"])
    updated_at: datetime = Field(..., examples=["2026-01-15T12:00:00Z"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "msg_01hxyzexample",
                    "client_ip": "127.0.0.1",
                    "raw_auth_user": "DOMAIN\\svc.msgate",
                    "sanitized_user": "svc.msgate",
                    "sender": "alerts@example.com",
                    "recipients": ["ops@example.com"],
                    "subject": "Test message",
                    "status": "queued",
                    "attempts": 0,
                    "last_error": None,
                    "created_at": "2026-01-15T12:00:00Z",
                    "updated_at": "2026-01-15T12:00:00Z",
                }
            ]
        }
    )
