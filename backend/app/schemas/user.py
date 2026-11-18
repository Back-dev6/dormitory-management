from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.core.security import validate_password_strength
from app.models.enums import Gender, Role

Password = Annotated[str, AfterValidator(validate_password_strength)]
Email = Annotated[EmailStr, AfterValidator(lambda v: v.lower())]
PHONE = r"^[0-9+ ]{8,15}$"
STUDENT_CODE = r"^[A-Za-z0-9]+$"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    student_code: str | None
    gender: Gender | None
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: Email
    password: Password
    full_name: str = Field(min_length=2, max_length=150)
    role: Role
    student_code: str | None = Field(default=None, min_length=3, max_length=20, pattern=STUDENT_CODE)
    gender: Gender | None = None
    phone: str | None = Field(default=None, pattern=PHONE)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, pattern=PHONE)
    student_code: str | None = Field(default=None, min_length=3, max_length=20, pattern=STUDENT_CODE)
    gender: Gender | None = None
    role: Role | None = None
    is_active: bool | None = None


class ResetPasswordIn(BaseModel):
    new_password: Password
