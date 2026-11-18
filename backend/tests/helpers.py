import base64
from datetime import date

PASSWORD = "Passw0rd123"
EMAILS = {
    "admin": "admin@test.vn", "mgr": "mgr@test.vn",
    "m1": "m1@test.vn", "m2": "m2@test.vn", "m3": "m3@test.vn", "f1": "f1@test.vn",
}
A101, A102, B101 = 1, 2, 3  # id phòng sau mỗi lần seed (A101: 2 giường, A102: 1 giường, B101: 4 giường)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def current_ym() -> tuple[int, int]:
    t = date.today()
    return t.year, t.month


def prev_ym() -> tuple[int, int]:
    y, m = current_ym()
    return (y - 1, 12) if m == 1 else (y, m - 1)


def next_ym() -> tuple[int, int]:
    y, m = current_ym()
    return (y + 1, 1) if m == 12 else (y, m + 1)


def approve_into(client, auth, student: str, room_id: int) -> tuple[int, int]:
    """Sinh viên gửi đơn, cán bộ duyệt. Trả về (contract_id, registration_id)."""
    r = client.post("/api/registrations", json={"room_id": room_id}, headers=auth(student))
    assert r.status_code == 201, r.text
    reg_id = r.json()["id"]
    r = client.post(f"/api/registrations/{reg_id}/approve", headers=auth("mgr"))
    assert r.status_code == 200, r.text
    return r.json()["contract"]["id"], reg_id


def post_reading(client, auth, room_id: int, ym: tuple[int, int], electric_new: int, water_new: int, **extra):
    body = {"room_id": room_id, "year": ym[0], "month": ym[1],
            "electric_new": electric_new, "water_new": water_new, **extra}
    return client.post("/api/utilities/readings", json=body, headers=auth("mgr"))


def make_student(email: str, gender: str = "MALE") -> int:
    from app.db.session import SessionLocal
    from app.models import User
    from app.models.enums import Gender, Role
    from tests.conftest import PASSWORD_HASH

    with SessionLocal() as db:
        u = User(email=email, password_hash=PASSWORD_HASH, full_name="SV " + email,
                 student_code=email.split("@")[0].upper(), gender=Gender(gender), role=Role.STUDENT)
        db.add(u)
        db.commit()
        return u.id
