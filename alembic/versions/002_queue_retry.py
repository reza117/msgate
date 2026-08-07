"""Schema v2: queue retry columns on messages."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_queue_retry"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("mime_payload", sa.Text(), nullable=True))
        batch.add_column(sa.Column("ews_username", sa.String(length=320), nullable=True))
        batch.add_column(
            sa.Column("ews_password_enc", sa.Text(), nullable=True),
        )
        batch.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_messages_next_retry", "messages", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_next_retry", table_name="messages")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("next_retry_at")
        batch.drop_column("ews_password_enc")
        batch.drop_column("ews_username")
        batch.drop_column("mime_payload")
