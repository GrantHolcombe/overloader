from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

Unit = Literal["lb", "kg"]


class CodeRequest(BaseModel):
    email: EmailStr


class CodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=12)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    unit: Unit


class TokenOut(BaseModel):
    token: str
    user: UserOut


class UserUpdate(BaseModel):
    unit: Unit


# The choices for custom exercises and the values catalog/exercises.csv may use, so the app's
# equipment filter stays a short, known list.
EQUIPMENT = ("Barbell", "Dumbbell", "Machine", "Cable", "Bodyweight", "Kettlebell", "Band", "Other")
MUSCLE_GROUPS = ("Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Full body", "Other")
Equipment = Literal[EQUIPMENT]
MuscleGroup = Literal[MUSCLE_GROUPS]


def _clean_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise ValueError("can't be empty")
    return name


ExerciseName = Annotated[str, Field(max_length=80), AfterValidator(_clean_name)]


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    equipment: str
    muscle_group: str
    custom: bool
    retired: bool


class ExerciseIn(BaseModel):
    name: ExerciseName
    equipment: Equipment
    muscle_group: MuscleGroup


class ExerciseUpdate(BaseModel):
    name: ExerciseName | None = None
    equipment: Equipment | None = None
    muscle_group: MuscleGroup | None = None


Weight = Annotated[Decimal, Field(ge=0, le=5000, max_digits=7, decimal_places=2)]
Reps = Annotated[int, Field(ge=1, le=1000)]
Sets = Annotated[int, Field(ge=1, le=100)]

# Clocks drift; allow a little slack before calling a time "in the future".
FUTURE_SLACK = timedelta(minutes=5)


def _not_future(value: datetime | None) -> datetime | None:
    if value is not None and value > datetime.now(UTC) + FUTURE_SLACK:
        raise ValueError("can't be in the future")
    return value


# Timezone required, so a past date means the same moment whatever the server's zone.
PerformedAt = Annotated[AwareDatetime, AfterValidator(_not_future)]


class SetIn(BaseModel):
    """One set of a per-set entry, in the entry's unit."""

    weight: Weight
    reps: Reps


SetDetails = Annotated[list[SetIn], Field(min_length=1, max_length=100)]


class LogIn(BaseModel):
    """Either quick (weight, reps and sets: every set the same) or per set (set_details, from
    which the summary weight/reps/sets are worked out)."""

    weight: Weight | None = None
    reps: Reps | None = None
    sets: Sets | None = None
    set_details: SetDetails | None = None
    # Defaults to the user's unit; set it when logging a past entry in another unit.
    unit: Unit | None = None
    # Defaults to now. Set it to log a past workout.
    performed_at: PerformedAt | None = None
    # Optional, picked by the app. Sending the same one again returns the saved entry (200)
    # instead of logging a duplicate, so the offline queue can retry safely.
    client_id: UUID | None = None

    @model_validator(mode="after")
    def _quick_or_per_set(self):
        quick = (self.weight, self.reps, self.sets)
        if self.set_details is not None:
            if any(v is not None for v in quick):
                raise ValueError("send weight/reps/sets or set_details, not both")
        elif any(v is None for v in quick):
            raise ValueError("weight, reps and sets are required (or send set_details)")
        return self


class LogUpdate(BaseModel):
    """Any subset of an entry's fields; omitted fields stay as they are.

    set_details replaces every set (and makes it a per-set entry). Sending weight, reps or sets
    without set_details makes it a quick entry again.
    """

    weight: Weight | None = None
    reps: Reps | None = None
    sets: Sets | None = None
    set_details: SetDetails | None = None
    unit: Unit | None = None
    performed_at: PerformedAt | None = None

    @model_validator(mode="after")
    def _not_both(self):
        if self.set_details is not None and any(
            v is not None for v in (self.weight, self.reps, self.sets)
        ):
            raise ValueError("send weight/reps/sets or set_details, not both")
        return self


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    weight: float
    reps: int


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    # For a per-set entry, these three summarize set_details: the heaviest set's weight and
    # reps, and how many sets.
    weight: float
    unit: Unit
    reps: int
    sets: int
    # Empty for a quick entry (every set the same).
    set_details: list[SetOut]
    performed_at: datetime


class LogWithExercise(LogOut):
    exercise: ExerciseOut


class RecentExercise(BaseModel):
    exercise: ExerciseOut
    last: LogOut
