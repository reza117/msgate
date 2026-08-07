"""Phase 5 observability tests."""

from __future__ import annotations

from unittest.mock import patch

from conftest import make_test_client, make_test_state
from msgate.config.export import export_config, import_config
from msgate.observability.ha import read_ha_status
from msgate.observability.metrics import MetricsRegistry
from msgate.observability.webhooks import WebhookNotifier
from msgate.schemas.config import EWSConfig, GatewayConfig, SMTPConfig


def test_metrics_prometheus_format() -> None:
    m = MetricsRegistry()
    m.inc_sent()
    m.inc_failed()
    text = m.prometheus_text()
    assert "msgate_messages_sent_total 1" in text
    assert "msgate_messages_failed_total 1" in text


def test_metrics_endpoint_public() -> None:
    client = make_test_client()
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "msgate_uptime_seconds" in r.text


def test_ha_status_defaults() -> None:
    status = read_ha_status()
    assert status.node_id == "node-1"
    assert status.role == "standalone"


def test_ha_status_from_env() -> None:
    env = {
        "MSGATE_NODE_ID": "node-a",
        "MSGATE_HA_ROLE": "active",
        "MSGATE_VRRP_STATE": "MASTER",
        "MSGATE_HA_LEADER": "node-a",
    }
    with patch.dict("os.environ", env, clear=False):
        status = read_ha_status()
    assert status.node_id == "node-a"
    assert status.role == "active"
    assert status.vrrp_state == "MASTER"


def test_config_export_import_roundtrip() -> None:
    state = make_test_state()
    cfg = GatewayConfig(
        smtp=SMTPConfig(port=1025),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            username="u@example.com",
            password="secret",
        ),
    )
    bundle = export_config(cfg, state.secret_box)
    restored = import_config(bundle, state.secret_box)
    assert restored.smtp.port == 1025
    assert restored.ews is not None
    assert restored.ews.password == "secret"


def test_config_import_api() -> None:
    state = make_test_state()
    cfg = GatewayConfig(
        smtp=SMTPConfig(port=2025),
        ews=EWSConfig(
            server_url="https://exchange.example.com/EWS/Exchange.asmx",
            username="u@example.com",
            password="secret",
        ),
    )
    bundle = export_config(cfg, state.secret_box)
    client = make_test_client(authenticated=True)
    r = client.post("/api/v1/config/import", json={"bundle": bundle})
    assert r.status_code == 200
    assert r.json()["smtp"]["port"] == 2025


def test_webhook_notifier_disabled_by_default() -> None:
    n = WebhookNotifier(urls=[])
    assert n.enabled is False


def test_event_hub_increments_metrics() -> None:
    from msgate.events.hub import EventHub

    metrics = MetricsRegistry()
    hub = EventHub(metrics=metrics)
    hub.publish_sync("queue.sent", "ok", id="1")
    assert metrics.messages_sent == 1
