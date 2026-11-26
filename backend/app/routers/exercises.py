from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on

from app.auth import DB, CurrentUser
from app.config import get_settings
from app.models import Exercise, LogEntry, User
from app.schemas import (
    ExerciseIn,
    ExerciseOut,
    ExerciseUpdate,
    LogIn,
    LogOut,
    LogUpdate,
    RecentExercise,
)

router = APIRouter(prefix="/api", tags=["exercises"])


@router.get("/exercises")
def list_exercises(user: CurrentUser, db: DB) -> list[ExerciseOut]:
    """The catalog (minus retired exercises) plus this user's own custom ones. About 90 rows;
    the app searches them on the device."""
    rows = db.scalars(
        select(Exercise)
        .where(
            or_(
                and_(Exercise.user_id.is_(None), Exercise.retired_at.is_(None)),
                Exercise.user_id == user.id,
            )
        )
        .order_by(func.lower(Exercise.name), Exercise.id)
    )
    return [ExerciseOut.model_validate(e) for e in rows]


def _name_taken(db: DB, user: User, name: str, except_id: int | None = None) -> bool:
    query = select(Exercise.id).where(
        Exercise.user_id == user.id, func.lower(Exercise.name) == name.lower()
    )
    if except_id is not None:
        query = query.where(Exercise.id != except_id)
    return db.scalar(query) is not None


@router.post("/exercises", status_code=status.HTTP_201_CREATED)
def create_exercise(body: ExerciseIn, user: CurrentUser, db: DB) -> ExerciseOut:
    """A custom exercise only this user sees. It may share a name with a catalog exercise."""
    limit = get_settings().custom_exercise_limit
    if limit is not None:
        count = db.scalar(select(func.count()).where(Exercise.user_id == user.id))
        if count >= limit:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"You can have up to {limit} custom exercises.",
            )
    if _name_taken(db, user, body.name):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"You already have an exercise called {body.name}."
        )
    exercise = Exercise(user_id=user.id, **body.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return ExerciseOut.model_validate(exercise)


def _own_custom_or_404(db: DB, user: User, exercise_id: int) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None or exercise.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such custom exercise")
    return exercise


@router.patch("/exercises/{exercise_id}")
def update_exercise(
    exercise_id: int, body: ExerciseUpdate, user: CurrentUser, db: DB
) -> ExerciseOut:
    exercise = _own_custom_or_404(db, user, exercise_id)
    changes = body.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Fields can't be empty")
    if "name" in changes and _name_taken(db, user, changes["name"], except_id=exercise.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"You already have an exercise called {changes['name']}."
        )
    for key, value in changes.items():
        setattr(exercise, key, value)
    db.commit()
    return ExerciseOut.model_validate(exercise)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, user: CurrentUser, db: DB) -> None:
    """Deletes a custom exercise and every entry logged against it."""
    exercise = _own_custom_or_404(db, user, exercise_id)
    db.execute(delete(LogEntry).where(LogEntry.exercise_id == exercise.id))
    db.delete(exercise)
    db.commit()


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


def _exercise_or_404(db: DB, user: User, exercise_id: int) -> Exercise:
    """A catalog exercise (retired ones too, so old history still opens) or the user's own
    custom one. Someone else's custom exercise is a 404, the same as one that doesn't exist."""
    exercise = db.get(Exercise, exercise_id)
    if exercise is None or (exercise.user_id is not None and exercise.user_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such exercise")
    return exercise


@router.get("/exercises/{exercise_id}")
def get_exercise(exercise_id: int, user: CurrentUser, db: DB) -> ExerciseOut:
    return ExerciseOut.model_validate(_exercise_or_404(db, user, exercise_id))


@router.get("/exercises/{exercise_id}/logs")
def list_logs(exercise_id: int, user: CurrentUser, db: DB) -> list[LogOut]:
    """Every entry for this exercise, newest first (history list and progress chart)."""
    _exercise_or_404(db, user, exercise_id)
    rows = db.scalars(
        select(LogEntry)
        .where(LogEntry.user_id == user.id, LogEntry.exercise_id == exercise_id)
        .order_by(LogEntry.performed_at.desc(), LogEntry.id.desc())
    )
    return [LogOut.model_validate(r) for r in rows]


@router.post("/exercises/{exercise_id}/logs", status_code=status.HTTP_201_CREATED)
def add_log(exercise_id: int, body: LogIn, user: CurrentUser, db: DB) -> LogOut:
    _exercise_or_404(db, user, exercise_id)
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


@router.patch("/logs/{log_id}")
def update_log(log_id: int, body: LogUpdate, user: CurrentUser, db: DB) -> LogOut:
    """Fixes a typo or moves an entry to another date. Only the fields sent change."""
    entry = db.scalar(select(LogEntry).where(LogEntry.id == log_id, LogEntry.user_id == user.id))
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such log entry")
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field} can't be empty")
        setattr(entry, field, value)
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
