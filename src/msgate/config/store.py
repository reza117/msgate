"""Persist GatewayConfig in SQLite with encrypted secrets."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from msgate.crypto.secrets import SecretBox
from msgate.db.models import SettingRow
from msgate.schemas.config import GatewayConfig

_CONFIG_KEY = "gateway_config"
_SECRET_FIELDS = (
    ("ews", "password"),
    ("graph", "client_secret"),
)


def _encrypt_secrets(data: dict, box: SecretBox) -> dict:
    out = json.loads(json.dumps(data))
    ews = out.get("ews")
    if isinstance(ews, dict) and ews.get("password"):
        ews["password"] = box.encrypt(ews["password"])
    graph = out.get("graph")
    if isinstance(graph, dict) and graph.get("client_secret"):
        graph["client_secret"] = box.encrypt(graph["client_secret"])
    return out


def _decrypt_secrets(data: dict, box: SecretBox) -> dict:
    out = json.loads(json.dumps(data))
    ews = out.get("ews")
    if isinstance(ews, dict) and ews.get("password"):
        try:
            ews["password"] = box.decrypt(ews["password"])
        except Exception:
            ews["password"] = ""
    graph = out.get("graph")
    if isinstance(graph, dict) and graph.get("client_secret"):
        try:
            graph["client_secret"] = box.decrypt(graph["client_secret"])
        except Exception:
            graph["client_secret"] = ""
    return out


def save_config(session: Session, config: GatewayConfig, box: SecretBox) -> None:
    payload = _encrypt_secrets(config.model_dump(mode="json"), box)
    row = session.get(SettingRow, _CONFIG_KEY)
    text = json.dumps(payload)
    if row is None:
        session.add(SettingRow(key=_CONFIG_KEY, value=text))
    else:
        row.value = text
    session.commit()


def load_config(session: Session, box: SecretBox) -> GatewayConfig | None:
    row = session.get(SettingRow, _CONFIG_KEY)
    if row is None:
        return None
    data = _decrypt_secrets(json.loads(row.value), box)
    return GatewayConfig.model_validate(data)


def redact_config(config: GatewayConfig) -> GatewayConfig:
    """Return copy with secrets masked for API responses."""
    data = config.model_dump(mode="json")
    ews = data.get("ews")
    if isinstance(ews, dict) and ews.get("password"):
        ews["password"] = "***"
    graph = data.get("graph")
    if isinstance(graph, dict) and graph.get("client_secret"):
        graph["client_secret"] = "***"
    return GatewayConfig.model_validate(data)


def merge_config_update(current: GatewayConfig, update: GatewayConfig) -> GatewayConfig:
    """Apply PUT payload; keep existing secrets when masked placeholder sent."""
    data = update.model_dump(mode="json")
    cur = current.model_dump(mode="json")
    ews = data.get("ews")
    cur_ews = cur.get("ews") or {}
    if isinstance(ews, dict):
        if ews.get("password") in (None, "", "***"):
            ews["password"] = cur_ews.get("password")
    graph = data.get("graph")
    cur_graph = cur.get("graph") or {}
    if isinstance(graph, dict):
        if graph.get("client_secret") in (None, "", "***"):
            graph["client_secret"] = cur_graph.get("client_secret")
    return GatewayConfig.model_validate(data)
