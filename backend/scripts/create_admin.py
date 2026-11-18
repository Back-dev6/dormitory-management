"""Tạo tài khoản Admin đầu tiên (dùng khi KHÔNG nạp dữ liệu mẫu).

Trong Docker:
    docker compose exec api python -m scripts.create_admin --email admin@truong.edu.vn
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password, validate_password_strength
from app.db.session import SessionLocal
from app.models import User
from app.models.enums import Role


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo tài khoản Admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Quản trị viên")
    args = parser.parse_args()

    password = getpass.getpass("Mật khẩu: ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        sys.exit("Hai mật khẩu không khớp")
    try:
        validate_password_strength(password)
    except ValueError as e:
        sys.exit(str(e))

    email = args.email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            sys.exit("Email này đã tồn tại")
        db.add(User(email=email, password_hash=hash_password(password), full_name=args.name, role=Role.ADMIN))
        db.commit()
    print(f"Đã tạo tài khoản Admin: {email}")


if __name__ == "__main__":
    main()
