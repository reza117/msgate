"""Auth-related configuration."""

from __future__ import annotations

import os

DEFAULT_HELP_URL = "https://msgate.github.io/msgate/"


def help_url() -> str:
    return os.environ.get("MSGATE_HELP_URL", DEFAULT_HELP_URL).strip()
