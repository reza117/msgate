"""Capacity evaluation tests."""

from __future__ import annotations

from conftest import memory_session_factory
from msgate.ops.alerts_config import OpsAlertsConfig, load_ops_alerts, save_ops_alerts
from msgate.ops.capacity import evaluate_capacity
from msgate.queue.circuit_breaker import CircuitBreaker


def test_ops_alerts_roundtrip() -> None:
    _e, sf = memory_session_factory()
    with sf() as session:
        cfg = OpsAlertsConfig(admin_email="ops@example.com", queue_warn_pending=50)
        save_ops_alerts(session, cfg)
        loaded = load_ops_alerts(session)
        assert loaded.admin_email == "ops@example.com"
        assert loaded.queue_warn_pending == 50


def test_evaluate_capacity_critical_on_circuit() -> None:
    _e, sf = memory_session_factory()
    br = CircuitBreaker(failure_threshold=1, cooldown_seconds=60)
    br.record_failure()
    with sf() as session:
        status = evaluate_capacity(
            session,
            pending=0,
            circuit=br,
            ops=OpsAlertsConfig(),
        )
    assert status.level == "critical"
    assert status.circuit_open
