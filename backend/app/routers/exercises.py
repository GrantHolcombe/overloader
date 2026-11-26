from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import distinct_on

from app.auth import DB, CurrentUser
from app.models import Exercise, LogEntry
from app.schemas import ExerciseOut, LogIn, LogOut, RecentExercise

router = APIRouter(prefix="/api", tags=["exercises"])


@router.get("/exercises")
def list_exercises(_: CurrentUser, db: DB) -> list[ExerciseOut]:
    """The whole catalog (about 90 rows); the app searches it on the device."""
    rows = db.scalars(select(Exercise).order_by(Exercise.name))
    return [ExerciseOut.model_validate(e) for e in rows]


@router.get("/exercises/recent")
def recent_exercises(user: CurrentUser, db: DB, limit: int = 8) -> list[RecentExercise]:
    """Exercises this user logged most recently, each with its latest entry."""
    latest = (
        select(LogEntry.id)
        .ext(distinct_on(LogEntry.exercise_id))
        .where(LogEntry.user_id == user.id)
        .order_by(LogEntry.exercise_id, LogEntry.performed_at.desc(), LogEntry.id.desc())
        .subquery()
    )
    entries = db.scalars(
        select(LogEntry)
        .where(LogEntry.id.in_(select(latest.c.id)))
        .order_by(LogEntry.performed_at.desc())
        .limit(min(max(limit, 1), 50))
    )
    return [
        RecentExercise(
            exercise=ExerciseOut.model_validate(e.exercise), last=LogOut.model_validate(e)
        )
        for e in entries
    ]


def _exercise_or_404(db: DB, exercise_id: int) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such exercise")
    return exercise


@router.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: int, _: CurrentUser, db: DB) -> ExerciseOut:
    return ExerciseOut.model_validate(_exercise_or_404(db, exercise_id))


@router.get("/exercises/{exercise_id}/logs")
def list_logs(exercise_id: int, user: CurrentUser, db: DB) -> list[LogOut]:
    """Every entry for this exercise, newest first (history list and progress chart)."""
    _exercise_or_404(db, exercise_id)
    rows = db.scalars(
        select(LogEntry)
        .where(LogEntry.user_id == user.id, LogEntry.exercise_id == exercise_id)
        .order_by(LogEntry.performed_at.desc(), LogEntry.id.desc())
    )
    return [LogOut.model_validate(r) for r in rows]


@router.post("/exercises/{exercise_id}/logs", status_code=status.HTTP_201_CREATED)
def add_log(exercise_id: int, body: LogIn, user: CurrentUser, db: DB) -> LogOut:
    _exercise_or_404(db, exercise_id)
    entry = LogEntry(
        user_id=user.id,
        exercise_id=exercise_id,
        weight=body.weight,
        unit=body.unit or user.unit,
        reps=body.reps,
        sets=body.sets,
    )
    if body.performed_at is not None:
        entry.performed_at = body.performed_at
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return LogOut.model_validate(entry)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(log_id: int, user: CurrentUser, db: DB) -> None:
    deleted = db.execute(
        delete(LogEntry).where(LogEntry.id == log_id, LogEntry.user_id == user.id)
    ).rowcount
    db.commit()
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such log entry")


@router.get("/stats")
def stats(user: CurrentUser, db: DB) -> dict:
    total, days = db.execute(
        select(func.count(), func.count(func.distinct(func.date(LogEntry.performed_at)))).where(
            LogEntry.user_id == user.id
        )
    ).one()
    return {"entries": total, "days": days}
