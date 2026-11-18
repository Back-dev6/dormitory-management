"""Đăng nhập, cấp/xoay vòng/thu hồi token.

Refresh token là JWT, nhưng CSDL lưu băm SHA-256 của nó để có thể THU HỒI:
- Mỗi lần refresh: token cũ bị thu hồi, cấp cặp token mới (xoay vòng).
- Nếu một token ĐÃ thu hồi bị dùng lại => nghi bị đánh cắp => thu hồi toàn bộ token của người đó.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.ratelimit import login_limiter
from app.core.security import (TokenError, burn_time, create_access_token, create_refresh_token,
                               decode_token, hash_token, verify_password)
from app.models import RefreshToken, User


def authenticate(db: Session, email: str, password: str, client_ip: str) -> User:
    email = email.strip().lower()
    key = f"{client_ip}|{email}"
    wait = login_limiter.retry_after(key)
    if wait:
        raise DomainError(429, f"Đăng nhập sai quá nhiều lần, thử lại sau {wait} giây",
                          headers={"Retry-After": str(wait)})
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        ok = verify_password(password, user.password_hash)
    else:
        burn_time(password)
        ok = False
    if not ok:  # cùng một thông báo cho "sai email" và "sai mật khẩu"
        login_limiter.record_failure(key)
        raise DomainError(401, "Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise DomainError(403, "Tài khoản đã bị khóa, hãy liên hệ ban quản lý")
    login_limiter.reset(key)
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str, int]:
    access, expires_in = create_access_token(user.id, user.role.value)
    refresh, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh), expires_at=expires_at))
    db.execute(delete(RefreshToken).where(
        RefreshToken.user_id == user.id, RefreshToken.expires_at < datetime.now(timezone.utc)))
    db.commit()
    return access, refresh, expires_in


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken)
               .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
               .values(revoked=True))
    db.commit()


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[User, tuple[str, str, int]]:
    try:
        decode_token(refresh_token, expected_type="refresh")
    except TokenError as e:
        raise DomainError(401, e.message)
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        .with_for_update().execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if row is None:
        db.rollback()
        raise DomainError(401, "Refresh token không hợp lệ")
    if row.revoked:
        user_id = row.user_id
        db.rollback()
        revoke_all(db, user_id)
        raise DomainError(401, "Refresh token đã bị thu hồi, vui lòng đăng nhập lại")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise DomainError(401, "Tài khoản không tồn tại hoặc đã bị khóa")
    row.revoked = True
    return user, issue_tokens(db, user)  # commit cả việc thu hồi token cũ và cấp token mới


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
               .values(revoked=True))
    db.commit()
