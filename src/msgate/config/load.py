"""Load and merge configuration from env + database."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from msgate.config.store import load_config, save_config
from msgate.config_load import load_config_from_env
from msgate.crypto.secrets import SecretBox
from msgate.schemas.config import GatewayConfig


def bootstrap_config(
    session_factory: sessionmaker,
    box: SecretBox,
) -> GatewayConfig:
    """Env seeds first run; DB overrides on subsequent starts."""
    env_cfg = load_config_from_env()
    with session_factory() as session:
        stored = load_config(session, box)
        if stored is None:
            save_config(session, env_cfg, box)
            return env_cfg
        return stored
