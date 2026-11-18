"""Băm mật khẩu (bcrypt) và JWT (access + refresh)."""
import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


class TokenError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------- mật khẩu ----------
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:  # hash hỏng/không hợp lệ
        return False


def burn_time(plain: str) -> None:
    """Tốn thời gian như khi kiểm tra thật, để không lộ email có tồn tại hay không."""
    verify_password(plain, _DUMMY_HASH)


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
    if len(password.encode()) > 72:  # giới hạn của bcrypt
        raise ValueError("Mật khẩu tối đa 72 byte")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Mật khẩu phải có cả chữ và số")
    return password


# ---------- JWT ----------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    now = _now()
    payload = {"sub": str(user_id), "role": role, "type": "access", "iat": now, "exp": now + lifetime}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    now = _now()
    expires = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "jti": uuid.uuid4().hex, "iat": now, "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM), expires


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],  # ghim thuật toán: chặn tấn công alg=none
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise TokenError("Token đã hết hạn")
    except jwt.InvalidTokenError:
        raise TokenError("Token không hợp lệ")
    if payload.get("type") != expected_type:
        raise TokenError("Sai loại token")
    return payload


def hash_token(token: str) -> str:
    """CSDL chỉ lưu băm SHA-256 của refresh token, không lưu token gốc."""
    return hashlib.sha256(token.encode()).hexdigest()
