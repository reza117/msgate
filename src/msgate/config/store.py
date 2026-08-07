"""Persist GatewayConfig in SQLite with encrypted secrets."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from msgate.crypto.secrets import SecretBox
from msgate.db.models import SettingRow
from msgate.schemas.config import GatewayConfig

_CONFIG_KEY = "gateway_config"


def _encrypt_field(block: dict | None, field: str, box: SecretBox) -> None:
    if isinstance(block, dict) and block.get(field):
        block[field] = box.encrypt(block[field])


def _decrypt_field(block: dict | None, field: str, box: SecretBox) -> None:
    if isinstance(block, dict) and block.get(field):
        try:
            block[field] = box.decrypt(block[field])
        except Exception:
            block[field] = ""


def _encrypt_secrets(data: dict, box: SecretBox) -> dict:
    out = json.loads(json.dumps(data))
    _encrypt_field(out.get("ews"), "password", box)
    _encrypt_field(out.get("ews_failover"), "password", box)
    _encrypt_field(out.get("graph"), "client_secret", box)
    return out


def _decrypt_secrets(data: dict, box: SecretBox) -> dict:
    out = json.loads(json.dumps(data))
    _decrypt_field(out.get("ews"), "password", box)
    _decrypt_field(out.get("ews_failover"), "password", box)
    _decrypt_field(out.get("graph"), "client_secret", box)
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
    for key in ("ews", "ews_failover"):
        block = data.get(key)
        if isinstance(block, dict) and block.get("password"):
            block["password"] = "***"
    graph = data.get("graph")
    if isinstance(graph, dict) and graph.get("client_secret"):
        graph["client_secret"] = "***"
    return GatewayConfig.model_validate(data)


def _merge_secret_block(data: dict, cur: dict, key: str, field: str) -> None:
    block = data.get(key)
    cur_block = cur.get(key) or {}
    if isinstance(block, dict) and block.get(field) in (None, "", "***"):
        block[field] = cur_block.get(field)


def merge_config_update(current: GatewayConfig, update: GatewayConfig) -> GatewayConfig:
    """Apply PUT payload; keep existing secrets when masked placeholder sent."""
    data = update.model_dump(mode="json")
    cur = current.model_dump(mode="json")
    _merge_secret_block(data, cur, "ews", "password")
    _merge_secret_block(data, cur, "ews_failover", "password")
    _merge_secret_block(data, cur, "graph", "client_secret")
    return GatewayConfig.model_validate(data)
