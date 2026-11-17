"""Ghi chỉ số điện nước và TỰ SINH hóa đơn trong cùng một giao dịch.

- Chỉ số cũ tự lấy từ tháng trước của phòng (nếu có), nên không thể nhập lệch.
- Khóa dòng phòng (FOR UPDATE) để hai cán bộ ghi cùng phòng không chen nhau,
  và để số người ở (occupied_beds) dùng tính tiền phòng không đổi giữa chừng.
- Tiền phòng = giá giường x số người đang ở tại thời điểm ghi chỉ số.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Invoice, Room, UtilityPrice, UtilityReading, User

CENT = Decimal("0.01")


def _fail(db: Session, status_code: int, detail: str):
    db.rollback()
    raise DomainError(status_code, detail)


def _due_date(year: int, month: int) -> date:
    return date(year + 1, 1, 10) if month == 12 else date(year, month + 1, 10)


def create_reading_and_invoice(
    db: Session, staff: User, room_id: int, month: int, year: int,
    electric_new: int, water_new: int,
    electric_old: int | None = None, water_old: int | None = None,
) -> tuple[UtilityReading, Invoice]:
    today = date.today()
    if (year, month) > (today.year, today.month):
        raise DomainError(422, "Không thể ghi chỉ số cho tháng trong tương lai")

    room = db.execute(
        select(Room).where(Room.id == room_id).with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if room is None:
        _fail(db, 404, "Không tìm thấy phòng")

    if db.scalar(select(UtilityReading.id).where(
            UtilityReading.room_id == room_id, UtilityReading.month == month,
            UtilityReading.year == year)):
        _fail(db, 409, f"Phòng đã có chỉ số tháng {month}/{year}")

    if db.scalar(select(UtilityReading.id).where(
            UtilityReading.room_id == room_id,
            or_(UtilityReading.year > year,
                and_(UtilityReading.year == year, UtilityReading.month > month)))):
        _fail(db, 409, "Phòng đã có chỉ số của tháng sau, không thể chèn tháng cũ")

    prev = db.scalar(
        select(UtilityReading).where(
            UtilityReading.room_id == room_id,
            or_(UtilityReading.year < year,
                and_(UtilityReading.year == year, UtilityReading.month < month)))
        .order_by(UtilityReading.year.desc(), UtilityReading.month.desc()).limit(1)
    )
    if prev is not None:
        e_old, w_old = prev.electric_new, prev.water_new
    else:
        e_old, w_old = electric_old or 0, water_old or 0

    if electric_new < e_old or water_new < w_old:
        _fail(db, 422, f"Chỉ số mới không được nhỏ hơn chỉ số cũ (điện cũ {e_old}, nước cũ {w_old})")

    price = db.scalar(
        select(UtilityPrice)
        .where(UtilityPrice.effective_from <= date(year, month, monthrange(year, month)[1]))
        .order_by(UtilityPrice.effective_from.desc()).limit(1)
    )
    if price is None:
        _fail(db, 409, "Chưa cấu hình đơn giá điện nước áp dụng cho tháng này")

    reading = UtilityReading(
        room_id=room_id, month=month, year=year, electric_old=e_old, electric_new=electric_new,
        water_old=w_old, water_new=water_new, recorded_by=staff.id,
    )
    db.add(reading)
    db.flush()

    electric_amount = (Decimal(electric_new - e_old) * price.electric_per_kwh).quantize(CENT)
    water_amount = (Decimal(water_new - w_old) * price.water_per_m3).quantize(CENT)
    room_fee = (room.price_per_bed * room.occupied_beds).quantize(CENT)
    invoice = Invoice(
        reading_id=reading.id, room_id=room_id, room_fee=room_fee,
        electric_amount=electric_amount, water_amount=water_amount,
        total=room_fee + electric_amount + water_amount, due_date=_due_date(year, month),
    )
    db.add(invoice)
    try:
        db.commit()
    except IntegrityError:
        _fail(db, 409, "Dữ liệu bị trùng hoặc vi phạm ràng buộc")
    db.refresh(reading)
    db.refresh(invoice)
    return reading, invoice
