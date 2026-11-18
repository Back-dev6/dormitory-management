from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.errors import DomainError
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Contract, User
from app.models.enums import ContractStatus, Role
from app.schemas.common import Page
from app.schemas.user import ResetPasswordIn, UserCreate, UserOut, UserUpdate
from app.services import auth_service

# Toàn bộ router này chỉ dành cho Admin
router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


def _get_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise DomainError(404, "Không tìm thấy tài khoản")
    return user


@router.get("", response_model=Page[UserOut], summary="Danh sách tài khoản (lọc theo vai trò, trạng thái, từ khóa)")
def list_users(
    role: Role | None = None, is_active: bool | None = None,
    q: str | None = Query(None, max_length=100, description="Tìm theo tên, email, mã sinh viên"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = []
    if role is not None:
        conds.append(User.role == role)
    if is_active is not None:
        conds.append(User.is_active == is_active)
    if q:
        like = f"%{q.strip()}%"
        conds.append(or_(User.full_name.ilike(like), User.email.ilike(like), User.student_code.ilike(like)))
    total = db.scalar(select(func.count()).select_from(User).where(*conds))
    users = db.scalars(select(User).where(*conds).order_by(User.id)
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[UserOut](items=[UserOut.model_validate(u) for u in users], total=total,
                         page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Admin tạo tài khoản (sinh viên, cán bộ hoặc admin)")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    if data.role == Role.STUDENT and (data.gender is None or not data.student_code):
        raise DomainError(422, "Tài khoản sinh viên bắt buộc có giới tính và mã sinh viên")
    user = User(email=data.email, password_hash=hash_password(data.password), full_name=data.full_name.strip(),
                role=data.role, student_code=data.student_code.upper() if data.student_code else None,
                gender=data.gender, phone=data.phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Email hoặc mã sinh viên đã tồn tại")
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut, summary="Chi tiết tài khoản")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserOut, summary="Sửa thông tin, đổi vai trò, khóa/mở tài khoản")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(get_current_user)):
    user = _get_or_404(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if user.id == admin.id and (changes.get("role", user.role) != user.role
                                or changes.get("is_active", user.is_active) is False):
        raise DomainError(409, "Không thể tự đổi vai trò hoặc tự khóa chính mình")
    new_role = changes.get("role")
    if new_role is not None and new_role != Role.STUDENT and user.role == Role.STUDENT:
        if db.scalar(select(Contract.id).where(Contract.student_id == user.id,
                                               Contract.status == ContractStatus.ACTIVE)):
            raise DomainError(409, "Sinh viên đang có hợp đồng hiệu lực, không thể đổi vai trò")
    if "student_code" in changes and changes["student_code"]:
        changes["student_code"] = changes["student_code"].upper()
    for key, value in changes.items():
        setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Mã sinh viên đã tồn tại")
    if changes.get("is_active") is False:
        auth_service.revoke_all(db, user.id)  # khóa tài khoản => thu hồi mọi phiên đăng nhập
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Admin đặt lại mật khẩu cho tài khoản (thu hồi mọi phiên)")
def reset_password(user_id: int, data: ResetPasswordIn, db: Session = Depends(get_db)):
    user = _get_or_404(db, user_id)
    user.password_hash = hash_password(data.new_password)
    db.commit()
    auth_service.revoke_all(db, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
