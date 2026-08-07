"""Settings and account UI tests."""

from __future__ import annotations

from conftest import make_test_client


def test_settings_page_requires_auth() -> None:
    from msgate.auth.admin import create_admin

    client = make_test_client(authenticated=False)
    state = client.app.state.msgate
    with state.session_factory() as session:
        create_admin(session, "testpass12", must_change_password=False)
    r = client.get("/ui/settings", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/ui/login"


def test_settings_page_renders_locked() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/ui/settings")
    assert r.status_code == 200
    assert b"Settings" in r.content
    assert b"startEdit()" in r.content
    assert b':disabled="!editing"' in r.content
    assert b"exchange.example.com" in r.content or b"mail.example.com" in r.content
    assert b'<span class="text-red-400">*</span>' in r.content
    assert b"password_set" in r.content
    assert b">Set<" in r.content
    assert b">Not set<" in r.content


def test_put_config_accepts_empty_default_sender() -> None:
    client = make_test_client(authenticated=True)
    cfg = client.get("/api/v1/config").json()
    cfg["default_sender"] = ""
    cfg["ews"]["password"] = "***"
    cfg["ews"]["primary_smtp"] = "svc@example.com"
    r = client.put("/api/v1/config", json=cfg)
    assert r.status_code == 200
    assert r.json()["default_sender"] is None


def test_account_page_change_password() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/ui/account")
    assert r.status_code == 200
    assert b"Change password" in r.content
    r = client.post(
        "/ui/auth/change-password",
        data={
            "current_password": "testpass12",
            "password": "newpass99",
            "password_confirm": "newpass99",
            "next": "/ui/account",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/ui/account?ok=1"
