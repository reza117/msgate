"""Auth-related configuration."""

from __future__ import annotations

import os

# External docs (optional). Sidebar Help uses in-app /ui/help instead.
DEFAULT_EXTERNAL_HELP_URL = "https://github.com/reza117/msgate/tree/main/docs"


def external_help_url() -> str:
    return os.environ.get("MSGATE_HELP_URL", DEFAULT_EXTERNAL_HELP_URL).strip()


def help_url() -> str:
    """Backward-compatible alias for external documentation URL."""
    return external_help_url()
