"""Chứng minh khóa giao dịch: nhiều cán bộ cùng duyệt đơn tranh chỗ cuối của một phòng.

Chạy (khi API đang chạy ở cổng 8000), từ thư mục backend:
    python -m scripts.demo_concurrency
Kỳ vọng: số duyệt thành công = số giường; phần còn lại nhận 409; occupied_beds không vượt max_beds.
"""
import threading
import uuid
from decimal import Decimal

import httpx
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import Building, Contract, Registration, Room, User
from app.models.enums import Gender

BASE = "http://127.0.0.1:8000"
BEDS = 2          # số giường của phòng thử
APPLICANTS = 6    # số đơn cùng được duyệt một lúc


def setup():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        manager = db.scalar(select(User).where(User.email == "canbo@ktx.edu.vn"))
        building = db.scalar(select(Building).where(Building.name == "Tòa A"))
        room = Room(building_id=building.id, room_number=f"T{suffix}", floor=9,
                    max_beds=BEDS, occupied_beds=0, price_per_bed=Decimal("100000"))
        students = [User(email=f"race{i}_{suffix}@test.local", password_hash="x",
                         full_name=f"SV thử {i}", student_code=f"R{i}{suffix}", gender=Gender.MALE)
                    for i in range(APPLICANTS)]
        db.add(room)
        db.add_all(students)
        db.flush()
        regs = [Registration(student_id=s.id, room_id=room.id) for s in students]
        db.add_all(regs)
        db.commit()
        return manager.id, room.id, [r.id for r in regs], [s.id for s in students]


def cleanup(room_id, student_ids):
    with SessionLocal() as db:
        db.execute(delete(Contract).where(Contract.room_id == room_id))
        db.execute(delete(Registration).where(Registration.room_id == room_id))
        db.execute(delete(User).where(User.id.in_(student_ids)))
        db.execute(delete(Room).where(Room.id == room_id))
        db.commit()


def main():
    try:
        httpx.get(f"{BASE}/api/health", timeout=5).raise_for_status()
    except httpx.HTTPError:
        raise SystemExit(f"Không kết nối được API tại {BASE}. Hãy chạy 'uvicorn app.main:app' ở cửa sổ CMD khác rồi thử lại.")
    manager_id, room_id, reg_ids, student_ids = setup()
    print(f"Phòng thử có {BEDS} giường, {APPLICANTS} đơn chờ duyệt, duyệt ĐỒNG THỜI...")
    barrier = threading.Barrier(APPLICANTS)
    results = []

    def approve(reg_id):
        with httpx.Client(base_url=BASE, timeout=60) as client:
            barrier.wait()  # tất cả cùng xuất phát một lúc
            r = client.post(f"/api/registrations/{reg_id}/approve",
                            headers={"X-User-Id": str(manager_id)}, json={})
            results.append((reg_id, r.status_code, r.json().get("detail", "OK")))

    threads = [threading.Thread(target=approve, args=(rid,)) for rid in reg_ids]
    [t.start() for t in threads]
    [t.join() for t in threads]

    for reg_id, code, msg in sorted(results):
        print(f"  đơn {reg_id}: HTTP {code} - {msg}")

    with SessionLocal() as db:
        room = db.get(Room, room_id)
        contracts = db.query(Contract).filter(Contract.room_id == room_id).count()
        ok = sum(1 for _, c, _ in results if c == 200)
        print(f"Kết quả: {ok} đơn thành công, occupied_beds = {room.occupied_beds}/{room.max_beds}, "
              f"số hợp đồng = {contracts}")
        passed = ok == BEDS and room.occupied_beds == BEDS and contracts == BEDS
    cleanup(room_id, student_ids)
    print("PASS: không xếp vượt chỗ." if passed else "FAIL: có lỗi đồng thời!")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
