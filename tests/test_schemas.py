"""Schema and DB model smoke checks."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from msgate.db.models import Base, MessageRow
from msgate.schemas import AuthType, EWSConfig, MessageStatus


def test_ews_config_defaults() -> None:
    ews = EWSConfig(server_url="https://exchange.example.com/EWS/Exchange.asmx")
    assert ews.auth_type == AuthType.NTLM
    assert ews.trust_self_signed is False


def test_sqlite_create_message_table() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        row = MessageRow(
            id="msg_test",
            client_ip="127.0.0.1",
            raw_auth_user=r"WDC\internal.wdc",
            sanitized_user="internal.wdc",
            sender="zabbix@example.com",
            recipients='["admin@example.com"]',
            subject="test",
            body="body",
            status=MessageStatus.QUEUED.value,
            attempts=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        assert session.get(MessageRow, "msg_test") is not None
