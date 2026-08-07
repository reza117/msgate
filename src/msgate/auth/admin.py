"""Admin user persistence and bootstrap."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session, sessionmaker

from msgate.auth.passwords import hash_password, verify_password
from msgate.db.models import AdminUserRow

ADMIN_USERNAME = "admin"
ENV_ADMIN_PASSWORD = "MSGATE_ADMIN_PASSWORD"


def admin_exists(session: Session) -> bool:
    return session.get(AdminUserRow, ADMIN_USERNAME) is not None


def get_admin(session: Session) -> AdminUserRow | None:
    return session.get(AdminUserRow, ADMIN_USERNAME)


def create_admin(
    session: Session,
    password: str,
    *,
    must_change_password: bool = False,
) -> AdminUserRow:
    row = AdminUserRow(
        username=ADMIN_USERNAME,
        password_hash=hash_password(password),
        must_change_password=must_change_password,
    )
    session.merge(row)
    session.commit()
    return row


def set_admin_password(
    session: Session,
    password: str,
    *,
    must_change_password: bool = False,
) -> AdminUserRow:
    row = get_admin(session)
    if row is None:
        return create_admin(session, password, must_change_password=must_change_password)
    row.password_hash = hash_password(password)
    row.must_change_password = must_change_password
    session.commit()
    session.refresh(row)
    return row


def check_admin_password(session: Session, password: str) -> bool:
    row = get_admin(session)
    if row is None:
        return False
    return verify_password(password, row.password_hash)


def bootstrap_admin_from_env(session_factory: sessionmaker) -> bool:
    """Create bootstrap admin from MSGATE_ADMIN_PASSWORD if none exists."""
    env_password = os.environ.get(ENV_ADMIN_PASSWORD)
    if not env_password:
        return False
    with session_factory() as session:
        if admin_exists(session):
            return False
        create_admin(session, env_password, must_change_password=True)
        return True
