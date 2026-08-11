"""Ops alert + digest settings stored in settings table (JSON)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from msgate.db.models import SettingRow

_KEY = "ops_alerts"


@dataclass
class OpsAlertsConfig:
    admin_email: str = ""
    webhook_url: str = ""
    email_alerts_enabled: bool = True
    queue_warn_pending: int = 100
    queue_critical_pending: int = 500
    queue_warn_age_seconds: int = 300
    alert_cooldown_seconds: int = 900
    # Digests (P5.5-11)
    digest_daily_enabled: bool = False
    digest_weekly_enabled: bool = False
    digest_subject: str = "[msgate] {period} digest"
    digest_include_body: bool = True
    digest_hour_utc: int = 6
    digest_weekday: int = 0  # Monday=0 … Sunday=6 (ISO)


def load_ops_alerts(session: Session) -> OpsAlertsConfig:
    row = session.get(SettingRow, _KEY)
    if row is None or not row.value.strip():
        return OpsAlertsConfig()
    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        return OpsAlertsConfig()
    base = OpsAlertsConfig()
    for field in asdict(base):
        if field in data:
            setattr(base, field, data[field])
    return base


def save_ops_alerts(session: Session, cfg: OpsAlertsConfig) -> None:
    from datetime import UTC, datetime

    text = json.dumps(asdict(cfg), separators=(",", ":"))
    row = session.get(SettingRow, _KEY)
    now = datetime.now(UTC)
    if row is None:
        session.add(SettingRow(key=_KEY, value=text, updated_at=now))
    else:
        row.value = text
        row.updated_at = now
    session.commit()
