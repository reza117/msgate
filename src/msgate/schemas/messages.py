"""Message request and queue record models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from msgate.schemas.enums import MessageStatus


class EmailMessageRequest(BaseModel):
    sender: EmailStr = Field(..., examples=["zabbix@domain.com"])
    recipients: list[EmailStr] = Field(..., examples=[["admin@domain.com"]])
    subject: str = Field(..., examples=["[PROBLEM] High CPU utilization"])
    body: str = Field(..., examples=["CPU load exceeded 95% on server01"])
    is_html: bool = False


class MessageRecord(BaseModel):
    id: str = Field(..., examples=["msg_984a1b2c"])
    client_ip: str = Field(..., examples=["127.0.0.1"])
    raw_auth_user: str = Field(..., examples=["WDC\\internal.wdc"])
    sanitized_user: str = Field(..., examples=["internal.wdc"])
    sender: EmailStr
    recipients: list[EmailStr]
    subject: str
    status: MessageStatus
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
