"""Message detail for inspector."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from msgate.schemas.enums import MessageStatus


class MessageDetail(BaseModel):
    id: str
    client_ip: str
    raw_auth_user: str
    sanitized_user: str
    sender: EmailStr
    recipients: list[EmailStr]
    subject: str
    status: MessageStatus
    attempts: int
    last_error: str | None
    mime_preview: str
    created_at: datetime
    updated_at: datetime
