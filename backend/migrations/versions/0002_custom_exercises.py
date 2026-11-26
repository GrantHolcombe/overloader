"""Custom exercises (owned by one user) and retiring catalog exercises.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL = the shared catalog; otherwise the one user who created it.
    op.add_column(
        "exercise",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("app_user.id", ondelete="CASCADE")),
    )
    # Set when a catalog exercise is removed from catalog/exercises.csv. It leaves the list but
    # keeps everyone's history; rows are never deleted.
    op.add_column("exercise", sa.Column("retired_at", sa.DateTime(timezone=True)))
    op.create_index("exercise_user", "exercise", ["user_id"])

    # Names were unique across the whole table. Now: unique (ignoring case) within the catalog,
    # and within each user's own exercises. A custom exercise may share a catalog name.
    op.drop_constraint("exercise_name_key", "exercise", type_="unique")
    op.create_index(
        "exercise_catalog_name",
        "exercise",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "exercise_user_name",
        "exercise",
        ["user_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("exercise_user_name", "exercise")
    op.drop_index("exercise_catalog_name", "exercise")
    op.execute(
        "DELETE FROM log_entry"
        " WHERE exercise_id IN (SELECT id FROM exercise WHERE user_id IS NOT NULL)"
    )
    op.execute("DELETE FROM exercise WHERE user_id IS NOT NULL")
    op.create_unique_constraint("exercise_name_key", "exercise", ["name"])
    op.drop_index("exercise_user", "exercise")
    op.drop_column("exercise", "retired_at")
    op.drop_column("exercise", "user_id")
