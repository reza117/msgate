"""Web auth tests."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from conftest import make_test_client, make_test_state
from msgate.api.app import create_app
from msgate.auth.admin import create_admin
from msgate.cli.admin import cmd_reset_password


def test_fresh_install_redirects_to_setup() -> None:
    client = make_test_client()
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/ui/setup"


def test_setup_creates_admin_and_logs_in() -> None:
    client = make_test_client()
    r = client.post(
        "/ui/auth/setup",
        data={"password": "testpass12", "password_confirm": "testpass12"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    r2 = client.get("/")
    assert r2.status_code == 200
    assert "Live Traffic" in r2.text


def test_api_requires_auth() -> None:
    client = make_test_client(authenticated=False)
    r = client.get("/api/v1/config")
    assert r.status_code == 401


def test_api_works_when_authenticated() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/api/v1/config")
    assert r.status_code == 200


def test_login_wrong_password() -> None:
    client = make_test_client()
    client.post(
        "/ui/auth/setup",
        data={"password": "testpass12", "password_confirm": "testpass12"},
    )
    client.post("/ui/auth/logout")
    r = client.post(
        "/ui/auth/login",
        data={"password": "wrong"},
        follow_redirects=False,
    )
    assert r.status_code == 401


def test_healthz_public() -> None:
    client = make_test_client()
    assert client.get("/healthz").status_code == 200


def test_env_bootstrap_forces_password_change() -> None:
    from msgate.auth.admin import bootstrap_admin_from_env

    with patch.dict(os.environ, {"MSGATE_ADMIN_PASSWORD": "bootstrap1"}):
        state = make_test_state()
        bootstrap_admin_from_env(state.session_factory)
        client = TestClient(create_app(state))
    r = client.post(
        "/ui/auth/login",
        data={"password": "bootstrap1"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/ui/change-password"


def test_change_password_clears_must_change() -> None:
    state = make_test_state()
    with state.session_factory() as session:
        create_admin(session, "bootstrap1", must_change_password=True)
    client = TestClient(create_app(state))
    client.post("/ui/auth/login", data={"password": "bootstrap1"})
    r = client.post(
        "/ui/auth/change-password",
        data={
            "current_password": "bootstrap1",
            "password": "newpass123",
            "password_confirm": "newpass123",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert client.get("/").status_code == 200


def test_reset_password_requires_root() -> None:
    with patch("msgate.cli.admin.os.geteuid", return_value=1000):
        assert cmd_reset_password() == 1


def test_help_link_in_dashboard() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/")
    assert "Help ↗" in r.text


def test_htmx_unauthenticated_gets_hx_redirect() -> None:
    """HTMX polls must not swap the login page into dashboard partials."""
    client = make_test_client()
    client.post(
        "/ui/auth/setup",
        data={"password": "testpass12", "password_confirm": "testpass12"},
    )
    client.post("/ui/auth/logout")
    r = client.get(
        "/ui/partials/stats",
        headers={"HX-Request": "true"},
        follow_redirects=False,
    )
    assert r.status_code == 401
    assert r.headers.get("HX-Redirect") == "/ui/login"
    assert "Sign in" not in r.text
