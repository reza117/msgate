"""Web UI and tools tests."""

from conftest import make_test_client
from msgate.tools.diagnostics import AuthSimRequest, simulate_auth


def test_ui_dashboard_html() -> None:
    r = make_test_client(authenticated=True).get("/")
    assert r.status_code == 200
    assert "msgate" in r.text
    assert "Live Traffic" in r.text


def test_auth_simulate_plain() -> None:
    import base64

    raw = base64.b64encode(b"\0WDC\\user\0pass").decode()
    result = simulate_auth(AuthSimRequest(mechanism="PLAIN", payload=raw, default_domain="WDC"))
    assert result.ok
    assert result.ews_username == r"WDC\user"
