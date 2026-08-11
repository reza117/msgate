"""Digest report / PDF / scheduler tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from unittest.mock import MagicMock

from conftest import make_test_client, make_test_state, memory_session_factory
from msgate.db.models import MessageRow
from msgate.ops.alerts_config import OpsAlertsConfig, save_ops_alerts
from msgate.ops.digest_pdf import text_pdf
from msgate.ops.digest_report import collect_digest
from msgate.ops.digest_scheduler import DigestScheduler, window_for
from msgate.ops.digest_state import DigestState, load_digest_state, save_digest_state
from msgate.schemas.enums import MessageStatus


def test_text_pdf_is_pdf() -> None:
    data = text_pdf("Title", ["line one", "line two"])
    assert data.startswith(b"%PDF-1.4")
    assert b"%%EOF" in data


def test_collect_digest_counts() -> None:
    _e, sf = memory_session_factory()
    now = datetime.now(UTC)
    start = now - timedelta(hours=12)
    with sf() as session:
        session.add(
            MessageRow(
                id="s1",
                client_ip="127.0.0.1",
                sender="a@example.com",
                recipients='["b@example.com"]',
                subject="ok",
                status=MessageStatus.SENT.value,
                created_at=start,
                updated_at=start + timedelta(seconds=90),
            )
        )
        session.add(
            MessageRow(
                id="f1",
                client_ip="127.0.0.1",
                sender="a@example.com",
                recipients='["b@example.com"]',
                subject="bad",
                status=MessageStatus.FAILED.value,
                last_error="EWS 503",
                created_at=start,
                updated_at=start + timedelta(minutes=5),
            )
        )
        session.commit()
        report = collect_digest(
            session,
            period="daily",
            window_start=now - timedelta(days=1),
            window_end=now + timedelta(seconds=1),
        )
    assert report.sent == 1
    assert report.failed == 1
    assert report.max_delay_seconds == 90.0
    assert report.max_delay_message_id == "s1"
    assert any("EWS 503" in e for e in report.top_errors)


def test_digest_scheduler_daily_once(monkeypatch) -> None:
    state = make_test_state()
    with state.session_factory() as session:
        save_ops_alerts(
            session,
            OpsAlertsConfig(
                admin_email="ops@example.com",
                digest_daily_enabled=True,
                digest_hour_utc=0,
            ),
        )

    mock_driver = MagicMock()
    mock_driver.is_configured.return_value = True
    mock_driver.send.return_value = MagicMock()
    monkeypatch.setattr("msgate.ops.digest_mail.resolve_driver", lambda _cfg: mock_driver)

    sched = DigestScheduler(state, interval=3600)
    now = datetime(2026, 8, 8, 10, 0, tzinfo=UTC)
    assert sched.tick(now=now) == ["daily"]
    assert mock_driver.send.call_count == 1
    req = mock_driver.send.call_args[0][0]
    mime = message_from_bytes(req.mime_bytes)
    assert "digest" in (mime["Subject"] or "").lower()
    assert b"application/pdf" in req.mime_bytes
    assert b"msgate-daily-digest.pdf" in req.mime_bytes
    assert b"JVBERi" in req.mime_bytes  # base64("%PDF")

    assert sched.tick(now=now) == []
    assert mock_driver.send.call_count == 1

    manual = sched.send_manual()
    assert manual.ok

    with state.session_factory() as session:
        st = load_digest_state(session)
    assert st.last_daily == "2026-08-08"


def test_window_for_weekly() -> None:
    now = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
    start, end = window_for("weekly", now)
    assert end == now
    assert (end - start).days == 7


def test_account_digest_ui_save() -> None:
    client = make_test_client(authenticated=True)
    r = client.post(
        "/ui/account/digests",
        data={
            "digest_daily_enabled": "1",
            "digest_subject": "[msgate] {period} ops",
            "digest_hour_utc": "7",
            "digest_weekday": "1",
            "digest_include_body": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "digests=1" in r.headers["location"]
    page = client.get("/ui/account")
    assert page.status_code == 200
    assert "Digest reports" in page.text
    assert "[msgate] {period} ops" in page.text


def test_digest_state_roundtrip() -> None:
    _e, sf = memory_session_factory()
    with sf() as session:
        save_digest_state(session, DigestState(last_daily="2026-01-01", last_weekly="2026-W01"))
        loaded = load_digest_state(session)
    assert loaded.last_daily == "2026-01-01"
    assert loaded.last_weekly == "2026-W01"
