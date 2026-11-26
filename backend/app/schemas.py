from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class LogIn(BaseModel):
    weight: Decimal = Field(ge=0, le=5000, max_digits=7, decimal_places=2)
    reps: int = Field(ge=1, le=1000)
    sets: int = Field(ge=1, le=100)
    # Defaults to the user's unit; set it when logging a past entry in another unit.
    unit: Unit | None = None
    performed_at: datetime | None = None


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
