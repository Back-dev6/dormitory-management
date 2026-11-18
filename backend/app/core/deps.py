from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models import User
from app.models.enums import Role

# tokenUrl giúp nút "Authorize" của Swagger đăng nhập được
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
_BEARER = {"WWW-Authenticate": "Bearer"}


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Xác định người dùng từ JWT access token (header Authorization: Bearer ...)."""
    if not token:
        raise HTTPException(401, "Chưa đăng nhập", headers=_BEARER)
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as e:
        raise HTTPException(401, e.message, headers=_BEARER)
    user = db.get(User, int(payload["sub"]))
    # Quyền lấy từ CSDL (không tin claim "role") nên đổi quyền/khóa tài khoản có hiệu lực ngay
    if user is None or not user.is_active:
        raise HTTPException(401, "Tài khoản không tồn tại hoặc đã bị khóa", headers=_BEARER)
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user

    return checker


STAFF = (Role.MANAGER, Role.ADMIN)
