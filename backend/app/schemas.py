from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

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


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    equipment: str
    muscle_group: str


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


class LogIn(BaseModel):
    weight: Weight
    reps: Reps
    sets: Sets
    # Defaults to the user's unit; set it when logging a past entry in another unit.
    unit: Unit | None = None
    # Defaults to now. Set it to log a past workout.
    performed_at: PerformedAt | None = None


class LogUpdate(BaseModel):
    """Any subset of an entry's fields; omitted fields stay as they are."""

    weight: Weight | None = None
    reps: Reps | None = None
    sets: Sets | None = None
    unit: Unit | None = None
    performed_at: PerformedAt | None = None


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    weight: float
    unit: Unit
    reps: int
    sets: int
    performed_at: datetime


class RecentExercise(BaseModel):
    exercise: ExerciseOut
    last: LogOut
