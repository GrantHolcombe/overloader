"""Per-set detail for a log entry.

An entry is still one row in log_entry. A quick entry (weight x reps x sets, every set the same)
has no log_set rows. A per-set entry has one log_set row per set, and its log_entry columns hold
a summary: the heaviest set's weight and reps, and the number of sets.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "log_set",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "log_entry_id",
            sa.Integer,
            sa.ForeignKey("log_entry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 1-based order within the entry.
        sa.Column("position", sa.Integer, nullable=False),
        # Same unit as the entry (log_entry.unit).
        sa.Column("weight", sa.Numeric(7, 2), nullable=False),
        sa.Column("reps", sa.Integer, nullable=False),
        sa.UniqueConstraint("log_entry_id", "position", name="log_set_entry_position"),
        sa.CheckConstraint("position BETWEEN 1 AND 100", name="log_set_position"),
        sa.CheckConstraint("weight >= 0 AND weight <= 5000", name="log_set_weight"),
        sa.CheckConstraint("reps BETWEEN 1 AND 1000", name="log_set_reps"),
    )


def downgrade() -> None:
    op.drop_table("log_set")
