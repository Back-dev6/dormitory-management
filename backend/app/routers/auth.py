from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import DomainError
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.models.enums import Role
from app.schemas.auth import (ChangePasswordIn, LoginIn, RefreshIn, RegisterIn, TokenOut)
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter()


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _token_out(user: User, tokens: tuple[str, str, int]) -> TokenOut:
    access, refresh, expires_in = tokens
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=expires_in,
                    user=UserOut.model_validate(user))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Sinh viên tự đăng ký tài khoản")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    user = User(email=data.email, password_hash=hash_password(data.password), full_name=data.full_name.strip(),
                student_code=data.student_code.upper(), gender=data.gender, phone=data.phone,
                role=Role.STUDENT)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Email hoặc mã sinh viên đã được đăng ký")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut, summary="Đăng nhập (JSON), nhận access + refresh token")
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, data.email, data.password, _ip(request))
    return _token_out(user, auth_service.issue_tokens(db, user))


@router.post("/token", response_model=TokenOut, include_in_schema=True,
             summary="Đăng nhập dạng form (cho nút Authorize của Swagger); username = email")
def login_form(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, form.username, form.password, _ip(request))
    return _token_out(user, auth_service.issue_tokens(db, user))


@router.post("/refresh", response_model=TokenOut, summary="Đổi refresh token lấy cặp token mới (xoay vòng)")
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    user, tokens = auth_service.rotate_refresh_token(db, data.refresh_token)
    return _token_out(user, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Đăng xuất: thu hồi refresh token")
def logout(data: RefreshIn, db: Session = Depends(get_db)):
    auth_service.revoke_refresh_token(db, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="Thông tin tài khoản đang đăng nhập")
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Đổi mật khẩu (thu hồi mọi refresh token)")
def change_password(data: ChangePasswordIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(data.old_password, user.password_hash):
        raise DomainError(400, "Mật khẩu cũ không đúng")
    if data.old_password == data.new_password:
        raise DomainError(422, "Mật khẩu mới phải khác mật khẩu cũ")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    auth_service.revoke_all(db, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
