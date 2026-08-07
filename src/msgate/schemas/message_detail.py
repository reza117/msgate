"""Message detail for inspector."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from msgate.schemas.enums import MessageStatus


class MessageDetail(BaseModel):
    """Full message inspector payload (OpenAPI examples are fictional)."""

    id: str = Field(..., examples=["msg_01hxyzexample"])
    client_ip: str = Field(..., examples=["127.0.0.1"])
    raw_auth_user: str = Field(..., examples=["DOMAIN\\svc.msgate"])
    sanitized_user: str = Field(..., examples=["svc.msgate"])
    sender: EmailStr = Field(..., examples=["alerts@example.com"])
    recipients: list[EmailStr] = Field(..., examples=[["ops@example.com"]])
    subject: str = Field(..., examples=["Test message"])
    status: MessageStatus = Field(..., examples=["sent"])
    attempts: int = Field(..., examples=[1])
    last_error: str | None = Field(default=None, examples=[None])
    mime_preview: str = Field(
        ...,
        examples=["From: alerts@example.com\r\nTo: ops@example.com\r\nSubject: Test\r\n\r\nHello\r\n"],
    )
    created_at: datetime = Field(..., examples=["2026-01-15T12:00:00Z"])
    updated_at: datetime = Field(..., examples=["2026-01-15T12:00:05Z"])

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
                    "status": "sent",
                    "attempts": 1,
                    "last_error": None,
                    "mime_preview": (
                        "From: alerts@example.com\r\n"
                        "To: ops@example.com\r\n"
                        "Subject: Test\r\n\r\nHello\r\n"
                    ),
                    "created_at": "2026-01-15T12:00:00Z",
                    "updated_at": "2026-01-15T12:00:05Z",
                }
            ]
        }
    )
