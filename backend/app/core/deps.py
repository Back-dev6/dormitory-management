from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.models.enums import Role


def get_current_user(
    x_user_id: Annotated[
        int | None,
        Header(description="TẠM THỜI (GĐ4): id người dùng. GĐ5 sẽ thay bằng JWT."),
    ] = None,
    db: Session = Depends(get_db),
) -> User:
    """Xác định người dùng hiện tại.

    Bản tạm: đọc header X-User-Id. Ở GĐ5 chỉ cần viết lại hàm này để đọc JWT,
    các router giữ nguyên vì chúng chỉ phụ thuộc vào get_current_user/require_roles.
    """
    if x_user_id is None:
        raise HTTPException(401, "Thiếu header X-User-Id (bản tạm, GĐ5 thay bằng JWT)")
    user = db.get(User, x_user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Người dùng không tồn tại hoặc đã bị khóa")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user

    return checker


STAFF = (Role.MANAGER, Role.ADMIN)
