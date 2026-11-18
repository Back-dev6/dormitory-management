"""Cấu hình pytest: dùng CSDL RIÊNG (mặc định tên `<db>_test`), không bao giờ đụng CSDL phát triển.

Cách chọn CSDL test (ưu tiên từ trên xuống):
  1. Biến môi trường TEST_DATABASE_URL
  2. DATABASE_URL trong .env, đổi tên CSDL thành `dorm_test`
Người dùng CSDL phải có quyền CREATE DATABASE (người dùng khai báo POSTGRES_USER trong Docker có quyền này).
"""
import os
import shutil
import tempfile
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def _test_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        from dotenv import dotenv_values
        base = os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL")
        if not base:
            raise RuntimeError("Thiếu DATABASE_URL (trong .env) hoặc TEST_DATABASE_URL")
        url = make_url(base).set(database="dorm_test").render_as_string(hide_password=False)
    assert make_url(url).database.endswith("_test"), "Tên CSDL test phải kết thúc bằng _test để tránh xóa nhầm dữ liệu thật"
    return url


def _ensure_database(url: str) -> None:
    u = make_url(url)
    admin = create_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": u.database}):
            conn.execute(text(f'CREATE DATABASE "{u.database}"'))
    admin.dispose()


# Phải đặt biến môi trường TRƯỚC khi import app (config đọc lúc import)
TEST_URL = _test_url()
STORAGE = tempfile.mkdtemp(prefix="dorm_storage_")
os.environ["DATABASE_URL"] = TEST_URL
os.environ["STORAGE_DIR"] = STORAGE
os.environ.setdefault("JWT_SECRET", "khoa-bi-mat-chi-dung-cho-pytest-0123456789")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.ratelimit import login_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Building, Room, User, UtilityPrice  # noqa: E402
from app.models.enums import Gender, Role  # noqa: E402
from tests.helpers import EMAILS, PASSWORD  # noqa: E402

PASSWORD_HASH = hash_password(PASSWORD)  # băm một lần, dùng chung cho mọi user test (bcrypt chậm có chủ đích)
_token_cache: dict[str, str] = {}


@pytest.fixture(scope="session", autouse=True)
def _database():
    _ensure_database(TEST_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    shutil.rmtree(STORAGE, ignore_errors=True)


@pytest.fixture(autouse=True)
def _fresh_data():
    """Mỗi test bắt đầu từ cùng một dữ liệu sạch."""
    login_limiter._events.clear()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + ", ".join(Base.metadata.tables) + " RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        def user(key, role, gender=None):
            return User(email=EMAILS[key], password_hash=PASSWORD_HASH, full_name=key.upper(), role=role,
                        gender=gender, student_code=key.upper() if role == Role.STUDENT else None)
        db.add_all([
            user("admin", Role.ADMIN), user("mgr", Role.MANAGER),
            user("m1", Role.STUDENT, Gender.MALE), user("m2", Role.STUDENT, Gender.MALE),
            user("m3", Role.STUDENT, Gender.MALE), user("f1", Role.STUDENT, Gender.FEMALE),
        ])
        a = Building(name="Tòa A", gender_type=Gender.MALE, floors=5)
        b = Building(name="Tòa B", gender_type=Gender.FEMALE, floors=5)
        db.add_all([a, b])
        db.flush()
        db.add_all([
            Room(building_id=a.id, room_number="A101", floor=1, max_beds=2, price_per_bed=Decimal("300000")),
            Room(building_id=a.id, room_number="A102", floor=1, max_beds=1, price_per_bed=Decimal("400000")),
            Room(building_id=b.id, room_number="B101", floor=1, max_beds=4, price_per_bed=Decimal("350000")),
        ])
        db.add(UtilityPrice(electric_per_kwh=Decimal("3500"), water_per_m3=Decimal("15000"),
                            effective_from=date(2020, 1, 1)))
        db.commit()


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    """auth("mgr") -> header Authorization của tài khoản đó (token được lưu đệm cho nhanh)."""
    def _auth(name: str) -> dict:
        if name not in _token_cache:
            r = client.post("/api/auth/login", json={"email": EMAILS[name], "password": PASSWORD})
            assert r.status_code == 200, r.text
            _token_cache[name] = r.json()["access_token"]
        return {"Authorization": f"Bearer {_token_cache[name]}"}
    return _auth
