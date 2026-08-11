"""Persist last digest send markers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from msgate.db.models import SettingRow

_KEY = "ops_digest_state"


@dataclass
class DigestState:
    last_daily: str = ""  # YYYY-MM-DD UTC
    last_weekly: str = ""  # YYYY-Www (ISO)


def load_digest_state(session: Session) -> DigestState:
    row = session.get(SettingRow, _KEY)
    if row is None or not row.value.strip():
        return DigestState()
    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        return DigestState()
    base = DigestState()
    for field in asdict(base):
        if field in data and isinstance(data[field], str):
            setattr(base, field, data[field])
    return base


def save_digest_state(session: Session, state: DigestState) -> None:
    text = json.dumps(asdict(state), separators=(",", ":"))
    row = session.get(SettingRow, _KEY)
    now = datetime.now(UTC)
    if row is None:
        session.add(SettingRow(key=_KEY, value=text, updated_at=now))
    else:
        row.value = text
        row.updated_at = now
    session.commit()
