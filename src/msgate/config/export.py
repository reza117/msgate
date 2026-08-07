"""Encrypted configuration bundle export/import."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from msgate.crypto.secrets import SecretBox
from msgate.schemas.config import GatewayConfig


class ConfigBundle(BaseModel):
    version: int = 1
    exported_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    config: dict


def export_config(config: GatewayConfig, box: SecretBox) -> str:
    bundle = ConfigBundle(config=config.model_dump(mode="json"))
    plaintext = bundle.model_dump_json()
    return box.encrypt(plaintext)


def import_config(token: str, box: SecretBox) -> GatewayConfig:
    plaintext = box.decrypt(token)
    bundle = ConfigBundle.model_validate(json.loads(plaintext))
    return GatewayConfig.model_validate(bundle.config)
