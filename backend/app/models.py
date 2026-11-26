from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    unit: Mapped[str] = mapped_column(String(2), server_default="lb")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("unit IN ('lb', 'kg')", name="app_user_unit"),)


class EmailLoginCode(Base):
    """One-time sign-in codes: hashed, short-lived, single use, limited guesses."""

    __tablename__ = "email_login_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    request_ip: Mapped[str | None] = mapped_column(String(45), index=True)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Exercise(Base):
    """A catalog exercise (user_id NULL, managed from catalog/exercises.csv) or a custom one
    that belongs to a single user."""

    __tablename__ = "exercise"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    equipment: Mapped[str] = mapped_column(String(20))
    muscle_group: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "exercise_catalog_name",
            func.lower(name),
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
        Index(
            "exercise_user_name",
            user_id,
            func.lower(name),
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    @property
    def custom(self) -> bool:
        return self.user_id is not None

    @property
    def retired(self) -> bool:
        return self.retired_at is not None


class LogEntry(Base):
    """One logged exercise: a weight lifted for `reps` reps, `sets` times."""

    __tablename__ = "log_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise.id"))
    # Stored in the unit it was entered in, so changing the display unit never rewrites history.
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    unit: Mapped[str] = mapped_column(String(2))
    reps: Mapped[int] = mapped_column(Integer)
    sets: Mapped[int] = mapped_column(Integer)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    exercise: Mapped[Exercise] = relationship()

    __table_args__ = (
        CheckConstraint("weight >= 0 AND weight <= 5000", name="log_entry_weight"),
        CheckConstraint("unit IN ('lb', 'kg')", name="log_entry_unit"),
        CheckConstraint("reps BETWEEN 1 AND 1000", name="log_entry_reps"),
        CheckConstraint("sets BETWEEN 1 AND 100", name="log_entry_sets"),
        Index("log_entry_user_exercise_time", "user_id", "exercise_id", "performed_at"),
    )
