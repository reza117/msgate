"""FastAPI endpoint tests."""

from __future__ import annotations

from conftest import make_test_client


def test_healthz() -> None:
    client = make_test_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_config_redacts_password() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    assert r.json()["ews"]["password"] == "***"


def test_get_config_blank_password_stays_null() -> None:
    from msgate.config.store import redact_config

    client = make_test_client(authenticated=True)
    state = client.app.state.msgate
    cfg = state.runtime.get()
    assert cfg.ews is not None
    cleared = cfg.model_copy(update={"ews": cfg.ews.model_copy(update={"password": None})})
    state.runtime.replace(cleared)
    redacted = redact_config(state.runtime.get()).model_dump(mode="json")
    assert redacted["ews"]["password"] in (None, "")
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    assert r.json()["ews"]["password"] in (None, "")


def test_put_config_hot_reload() -> None:
    client = make_test_client(authenticated=True)
    cfg = client.get("/api/v1/config").json()
    cfg["smtp"]["port"] = 2525
    r = client.put("/api/v1/config", json=cfg)
    assert r.status_code == 200
    assert r.json()["smtp"]["port"] == 2525
