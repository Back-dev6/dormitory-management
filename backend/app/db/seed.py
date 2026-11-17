from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import bcrypt
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import (Building, Contract, Registration, Room, User, UtilityPrice)
from app.models.enums import (ContractStatus, Gender, RegistrationStatus, Role)


def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "admin@ktx.edu.vn")):
            print("Seed đã chạy trước đó, bỏ qua.")
            return

        admin = User(email="admin@ktx.edu.vn", password_hash=hash_pw("Admin@123"),
                     full_name="Quản trị viên", role=Role.ADMIN)
        manager = User(email="canbo@ktx.edu.vn", password_hash=hash_pw("Canbo@123"),
                       full_name="Cán bộ Quản lý", role=Role.MANAGER)
        sv1 = User(email="sv1@ktx.edu.vn", password_hash=hash_pw("Sv@12345"),
                   full_name="Nguyễn Văn An", student_code="SV001", gender=Gender.MALE)
        sv2 = User(email="sv2@ktx.edu.vn", password_hash=hash_pw("Sv@12345"),
                   full_name="Trần Văn Bình", student_code="SV002", gender=Gender.MALE)
        sv3 = User(email="sv3@ktx.edu.vn", password_hash=hash_pw("Sv@12345"),
                   full_name="Lê Thị Cúc", student_code="SV003", gender=Gender.FEMALE)
        db.add_all([admin, manager, sv1, sv2, sv3])

        a = Building(name="Tòa A", gender_type=Gender.MALE, address="Khu KTX phía Đông", floors=5)
        b = Building(name="Tòa B", gender_type=Gender.FEMALE, address="Khu KTX phía Tây", floors=5)
        db.add_all([a, b])
        db.flush()

        a101 = Room(building_id=a.id, room_number="A101", floor=1, max_beds=4,
                    occupied_beds=1, price_per_bed=Decimal("350000"))
        a102 = Room(building_id=a.id, room_number="A102", floor=1, max_beds=2,
                    occupied_beds=0, price_per_bed=Decimal("400000"))
        a201 = Room(building_id=a.id, room_number="A201", floor=2, max_beds=4,
                    occupied_beds=0, price_per_bed=Decimal("300000"))
        b101 = Room(building_id=b.id, room_number="B101", floor=1, max_beds=4,
                    occupied_beds=0, price_per_bed=Decimal("350000"))
        b102 = Room(building_id=b.id, room_number="B102", floor=1, max_beds=6,
                    occupied_beds=0, price_per_bed=Decimal("250000"))
        db.add_all([a101, a102, a201, b101, b102])
        db.flush()

        db.add(UtilityPrice(electric_per_kwh=Decimal("3500"),
                            water_per_m3=Decimal("15000"),
                            effective_from=date(2026, 1, 1)))

        # SV1 đang ở A101: đơn đã duyệt + hợp đồng hiệu lực (khớp occupied_beds = 1)
        reg = Registration(student_id=sv1.id, room_id=a101.id,
                           status=RegistrationStatus.APPROVED, reviewed_by=manager.id,
                           reviewed_at=datetime.now(timezone.utc))
        db.add(reg)
        db.flush()
        today = date.today()
        db.add(Contract(registration_id=reg.id, student_id=sv1.id, room_id=a101.id,
                        start_date=today, end_date=today + timedelta(days=180),
                        status=ContractStatus.ACTIVE))
        db.commit()
        print("Seed thành công.")


if __name__ == "__main__":
    seed()
