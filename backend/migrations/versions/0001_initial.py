"""Users, sign-in codes, the exercise catalog and log entries.

Revision ID: 0001
Revises:
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Common gym exercises: (name, equipment, muscle group). Later additions go in new migrations.
EXERCISES = [
    # Barbell
    ("Back Squat", "Barbell", "Legs"),
    ("Front Squat", "Barbell", "Legs"),
    ("Deadlift", "Barbell", "Back"),
    ("Sumo Deadlift", "Barbell", "Back"),
    ("Romanian Deadlift", "Barbell", "Legs"),
    ("Bench Press", "Barbell", "Chest"),
    ("Incline Bench Press", "Barbell", "Chest"),
    ("Decline Bench Press", "Barbell", "Chest"),
    ("Close-Grip Bench Press", "Barbell", "Arms"),
    ("Overhead Press", "Barbell", "Shoulders"),
    ("Barbell Row", "Barbell", "Back"),
    ("Hip Thrust", "Barbell", "Legs"),
    ("Barbell Curl", "Barbell", "Arms"),
    ("Barbell Shrug", "Barbell", "Back"),
    ("Barbell Lunge", "Barbell", "Legs"),
    ("Good Morning", "Barbell", "Legs"),
    ("EZ-Bar Curl", "Barbell", "Arms"),
    ("Skull Crusher", "Barbell", "Arms"),
    ("Trap Bar Deadlift", "Barbell", "Legs"),
    # Dumbbell
    ("Dumbbell Bench Press", "Dumbbell", "Chest"),
    ("Incline Dumbbell Press", "Dumbbell", "Chest"),
    ("Dumbbell Fly", "Dumbbell", "Chest"),
    ("Dumbbell Shoulder Press", "Dumbbell", "Shoulders"),
    ("Arnold Press", "Dumbbell", "Shoulders"),
    ("Lateral Raise", "Dumbbell", "Shoulders"),
    ("Front Raise", "Dumbbell", "Shoulders"),
    ("Rear Delt Fly", "Dumbbell", "Shoulders"),
    ("Dumbbell Row", "Dumbbell", "Back"),
    ("Dumbbell Curl", "Dumbbell", "Arms"),
    ("Hammer Curl", "Dumbbell", "Arms"),
    ("Concentration Curl", "Dumbbell", "Arms"),
    ("Overhead Triceps Extension", "Dumbbell", "Arms"),
    ("Triceps Kickback", "Dumbbell", "Arms"),
    ("Goblet Squat", "Dumbbell", "Legs"),
    ("Dumbbell Lunge", "Dumbbell", "Legs"),
    ("Bulgarian Split Squat", "Dumbbell", "Legs"),
    ("Dumbbell Romanian Deadlift", "Dumbbell", "Legs"),
    ("Dumbbell Shrug", "Dumbbell", "Back"),
    ("Dumbbell Pullover", "Dumbbell", "Chest"),
    # Machine
    ("Leg Press", "Machine", "Legs"),
    ("Hack Squat", "Machine", "Legs"),
    ("Smith Machine Squat", "Machine", "Legs"),
    ("Leg Extension", "Machine", "Legs"),
    ("Seated Leg Curl", "Machine", "Legs"),
    ("Lying Leg Curl", "Machine", "Legs"),
    ("Standing Calf Raise", "Machine", "Legs"),
    ("Seated Calf Raise", "Machine", "Legs"),
    ("Hip Abductor", "Machine", "Legs"),
    ("Hip Adductor", "Machine", "Legs"),
    ("Glute Kickback Machine", "Machine", "Legs"),
    ("Chest Press Machine", "Machine", "Chest"),
    ("Smith Machine Bench Press", "Machine", "Chest"),
    ("Pec Deck", "Machine", "Chest"),
    ("Shoulder Press Machine", "Machine", "Shoulders"),
    ("Reverse Pec Deck", "Machine", "Shoulders"),
    ("Lat Pulldown", "Machine", "Back"),
    ("Seated Row Machine", "Machine", "Back"),
    ("T-Bar Row", "Machine", "Back"),
    ("Assisted Pull-Up", "Machine", "Back"),
    ("Back Extension", "Machine", "Back"),
    ("Preacher Curl Machine", "Machine", "Arms"),
    ("Triceps Dip Machine", "Machine", "Arms"),
    ("Ab Crunch Machine", "Machine", "Core"),
    # Cable
    ("Seated Cable Row", "Cable", "Back"),
    ("Straight-Arm Pulldown", "Cable", "Back"),
    ("Face Pull", "Cable", "Shoulders"),
    ("Cable Lateral Raise", "Cable", "Shoulders"),
    ("Cable Fly", "Cable", "Chest"),
    ("Cable Crossover", "Cable", "Chest"),
    ("Triceps Pushdown", "Cable", "Arms"),
    ("Overhead Cable Triceps Extension", "Cable", "Arms"),
    ("Cable Curl", "Cable", "Arms"),
    ("Cable Crunch", "Cable", "Core"),
    ("Cable Woodchopper", "Cable", "Core"),
    ("Cable Pull-Through", "Cable", "Legs"),
    # Bodyweight (log added weight, or 0)
    ("Pull-Up", "Bodyweight", "Back"),
    ("Chin-Up", "Bodyweight", "Back"),
    ("Inverted Row", "Bodyweight", "Back"),
    ("Dip", "Bodyweight", "Chest"),
    ("Push-Up", "Bodyweight", "Chest"),
    ("Hanging Leg Raise", "Bodyweight", "Core"),
    ("Sit-Up", "Bodyweight", "Core"),
    # Kettlebell
    ("Kettlebell Swing", "Kettlebell", "Legs"),
    ("Kettlebell Goblet Squat", "Kettlebell", "Legs"),
    ("Kettlebell Press", "Kettlebell", "Shoulders"),
    ("Turkish Get-Up", "Kettlebell", "Core"),
]


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("unit", sa.String(2), nullable=False, server_default="lb"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("unit IN ('lb', 'kg')", name="app_user_unit"),
    )
    op.create_table(
        "email_login_code",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, index=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("request_ip", sa.String(45), index=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    exercise = op.create_table(
        "exercise",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("equipment", sa.String(20), nullable=False),
        sa.Column("muscle_group", sa.String(20), nullable=False),
    )
    op.create_table(
        "log_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exercise_id", sa.Integer, sa.ForeignKey("exercise.id"), nullable=False),
        sa.Column("weight", sa.Numeric(7, 2), nullable=False),
        sa.Column("unit", sa.String(2), nullable=False),
        sa.Column("reps", sa.Integer, nullable=False),
        sa.Column("sets", sa.Integer, nullable=False),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("weight >= 0 AND weight <= 5000", name="log_entry_weight"),
        sa.CheckConstraint("unit IN ('lb', 'kg')", name="log_entry_unit"),
        sa.CheckConstraint("reps BETWEEN 1 AND 1000", name="log_entry_reps"),
        sa.CheckConstraint("sets BETWEEN 1 AND 100", name="log_entry_sets"),
    )
    op.create_index(
        "log_entry_user_exercise_time", "log_entry", ["user_id", "exercise_id", "performed_at"]
    )
    op.bulk_insert(
        exercise,
        [{"name": n, "equipment": eq, "muscle_group": mg} for n, eq, mg in EXERCISES],
    )


def downgrade() -> None:
    op.drop_table("log_entry")
    op.drop_table("exercise")
    op.drop_table("email_login_code")
    op.drop_table("app_user")
