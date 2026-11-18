import threading

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.main import app
from app.models import Contract, Registration, Room
from tests.helpers import A101, make_student


def test_concurrent_approvals_never_oversell_a_room(auth):
    """5 đơn cùng được duyệt một lúc cho phòng 2 giường: phải đúng 2 thành công, 3 bị 409."""
    manager = auth("mgr")
    student_ids = [make_student(f"race{i}@test.vn") for i in range(5)]
    with SessionLocal() as db:
        regs = [Registration(student_id=sid, room_id=A101) for sid in student_ids]
        db.add_all(regs)
        db.commit()
        reg_ids = [r.id for r in regs]

    barrier = threading.Barrier(len(reg_ids))
    results: list[tuple[int, str]] = []

    def approve(reg_id: int) -> None:
        local_client = TestClient(app)  # mỗi luồng một client riêng
        barrier.wait()  # cùng xuất phát một lúc
        r = local_client.post(f"/api/registrations/{reg_id}/approve", headers=manager)
        results.append((r.status_code, "" if r.status_code == 200 else r.json()["detail"]))

    threads = [threading.Thread(target=approve, args=(rid,)) for rid in reg_ids]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert sorted(c for c, _ in results) == [200, 200, 409, 409, 409]
    # 409 phải do kiểm tra "hết chỗ" sau khi chờ khóa, không phải do CHECK của CSDL bắt lỗi muộn
    assert all("hết chỗ" in detail for code, detail in results if code == 409)
    with SessionLocal() as db:
        assert db.get(Room, A101).occupied_beds == 2
        assert db.scalar(select(func.count()).select_from(Contract).where(Contract.room_id == A101)) == 2
