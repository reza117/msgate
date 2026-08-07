"""Admin CLI commands."""

from __future__ import annotations

import getpass
import os
import sys

from msgate.app.bootstrap import build_app_state
from msgate.auth.admin import set_admin_password


def cmd_reset_password() -> int:
    if os.geteuid() != 0:
        print("msgate admin reset-password must be run as root (uid 0).", file=sys.stderr)
        return 1

    password = getpass.getpass("New admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        state = build_app_state()
        with state.session_factory() as session:
            set_admin_password(session, password, must_change_password=True)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Admin password updated. User must set a new password on next login.")
    return 0
