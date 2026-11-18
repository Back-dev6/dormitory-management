from pydantic import BaseModel, Field

from app.models.enums import Gender
from app.schemas.user import PHONE, STUDENT_CODE, Email, Password, UserOut


class RegisterIn(BaseModel):
    """Sinh viên tự đăng ký. Vai trò luôn là STUDENT, không nhận trường role từ client."""
    email: Email
    password: Password
    full_name: str = Field(min_length=2, max_length=150)
    student_code: str = Field(min_length=3, max_length=20, pattern=STUDENT_CODE)
    gender: Gender
    phone: str | None = Field(default=None, pattern=PHONE)


class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    old_password: str = Field(max_length=200)
    new_password: Password


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # số giây hiệu lực của access token
    user: UserOut
