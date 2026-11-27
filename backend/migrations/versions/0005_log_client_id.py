"""An id the app picks for each new log entry, so retries can't log it twice.

The app saves entries offline and sends them when signal returns. If a request reaches the API
but the reply is lost (common on gym Wi-Fi), the app sends it again. With the same client_id the
API returns the entry it already saved instead of adding a duplicate.

Nullable: older entries and API clients that don't send one are unaffected.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("log_entry", sa.Column("client_id", postgresql.UUID(as_uuid=True)))
    op.create_index(
        "log_entry_user_client_id",
        "log_entry",
        ["user_id", "client_id"],
        unique=True,
        postgresql_where=sa.text("client_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("log_entry_user_client_id", table_name="log_entry")
    op.drop_column("log_entry", "client_id")
