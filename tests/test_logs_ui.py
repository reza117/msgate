"""Tests for on-disk log search and Logs UI."""

from __future__ import annotations

from pathlib import Path

from conftest import make_test_client
from msgate.observability.log_reader import list_log_files, search_logs


def test_search_logs_filters(tmp_path: Path) -> None:
    day = "20260808"
    path = tmp_path / f"msgate-{day}.log"
    path.write_text(
        "\n".join(
            [
                "2026-08-08T10:00:00 INFO [msgate.smtp] peer=10.0.0.1 accepted",
                "2026-08-08T10:01:00 ERROR [msgate.queue] message_id=abc failed",
                "2026-08-08T10:02:00 WARNING [msgate.ews] timeout",
                "orphan line without format",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert len(list_log_files(directory=tmp_path)) == 1
    errors = search_logs(level="ERROR", directory=tmp_path)
    assert len(errors) == 1
    assert errors[0].message.endswith("failed")

    by_q = search_logs(query="message_id=abc", directory=tmp_path)
    assert len(by_q) == 1

    by_logger = search_logs(logger="smtp", directory=tmp_path)
    assert len(by_logger) == 1
    assert "peer=10.0.0.1" in by_logger[0].message

    by_day = search_logs(day=day, directory=tmp_path, limit=10)
    assert len(by_day) == 4


def test_ui_logs_requires_auth() -> None:
    client = make_test_client(authenticated=False)
    r = client.get("/ui/logs", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] in ("/ui/setup", "/ui/login")


def test_ui_logs_page_renders(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "msgate-20260808.log"
    log_path.write_text(
        "2026-08-08T12:00:00 INFO [msgate.test] hello from logs ui\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MSGATE_LOG_DIR", str(tmp_path))

    client = make_test_client(authenticated=True)
    r = client.get("/ui/logs")
    assert r.status_code == 200
    assert "Logs" in r.text
    assert "hello from logs ui" in r.text
    assert 'href="/ui/logs"' in r.text

    r2 = client.get("/ui/logs", params={"q": "hello", "level": "INFO"})
    assert r2.status_code == 200
    assert "hello from logs ui" in r2.text

    r3 = client.get("/ui/logs", params={"q": "nomatch-xyz"})
    assert r3.status_code == 200
    assert "No matching log lines" in r3.text
