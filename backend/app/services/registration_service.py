"""Nghiệp vụ đăng ký phòng, duyệt đơn, hợp đồng, kèm KHÓA GIAO DỊCH.

Quy tắc:
- Đơn PENDING KHÔNG giữ chỗ. Chỉ khi DUYỆT mới tăng occupied_beds.
- Thứ tự khóa luôn là: đơn (registrations) -> hợp đồng (contracts) -> phòng (rooms).
  Mọi giao dịch khóa theo cùng một thứ tự nên không thể xảy ra deadlock.
- Mọi hàm đều tự commit/rollback; gặp lỗi nghiệp vụ thì rollback để NHẢ KHÓA ngay.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError
from app.models import Contract, Registration, Room, User
from app.models.enums import ContractStatus, RegistrationStatus

LOCKED = {"populate_existing": True}  # buộc đọc lại dữ liệu mới sau khi chờ khóa


def _lock_registration(db: Session, registration_id: int) -> Registration:
    reg = db.execute(
        select(Registration)
        .where(Registration.id == registration_id)
        .with_for_update()
        .execution_options(**LOCKED)
    ).scalar_one_or_none()
    if reg is None:
        db.rollback()
        raise DomainError(404, "Không tìm thấy đơn đăng ký")
    return reg


def _lock_room(db: Session, room_id: int) -> Room:
    return db.execute(
        select(Room).where(Room.id == room_id).with_for_update().execution_options(**LOCKED)
    ).scalar_one()


def _fail(db: Session, status_code: int, detail: str):
    db.rollback()  # nhả khóa trước khi báo lỗi
    raise DomainError(status_code, detail)


def create_registration(db: Session, student: User, room_id: int) -> Registration:
    room = db.execute(
        select(Room).options(joinedload(Room.building)).where(Room.id == room_id)
    ).scalar_one_or_none()
    if room is None:
        raise DomainError(404, "Không tìm thấy phòng")
    if student.gender is None:
        raise DomainError(422, "Hồ sơ của bạn chưa có giới tính, hãy liên hệ ban quản lý")
    if student.gender != room.building.gender_type:
        raise DomainError(409, f"{room.building.name} chỉ dành cho sinh viên "
                               f"{'nam' if room.building.gender_type.value == 'MALE' else 'nữ'}")
    has_contract = db.scalar(
        select(Contract.id).where(
            Contract.student_id == student.id, Contract.status == ContractStatus.ACTIVE
        )
    )
    if has_contract:
        raise DomainError(409, "Bạn đang có hợp đồng còn hiệu lực")
    has_pending = db.scalar(
        select(Registration.id).where(
            Registration.student_id == student.id,
            Registration.status == RegistrationStatus.PENDING,
        )
    )
    if has_pending:
        raise DomainError(409, "Bạn đã có một đơn đang chờ duyệt")
    if room.occupied_beds >= room.max_beds:
        raise DomainError(409, "Phòng đã hết chỗ")

    reg = Registration(student_id=student.id, room_id=room.id)
    db.add(reg)
    try:
        db.commit()
    except IntegrityError:  # hai request cùng lọt qua bước kiểm tra: partial unique index chặn
        db.rollback()
        raise DomainError(409, "Bạn đã có một đơn đang chờ duyệt")
    db.refresh(reg)
    return reg


def approve_registration(
    db: Session, registration_id: int, manager: User,
    start_date: date | None = None, months: int = 6,
) -> tuple[Registration, Contract]:
    # B1: khóa dòng đơn -> hai người cùng duyệt MỘT đơn sẽ xếp hàng, người sau thấy đơn đã xử lý
    reg = _lock_registration(db, registration_id)
    if reg.status != RegistrationStatus.PENDING:
        _fail(db, 409, f"Đơn đã ở trạng thái {reg.status.value}, không thể duyệt")

    # B2: khóa dòng phòng -> các đơn KHÁC NHAU tranh cùng phòng cũng xếp hàng
    room = _lock_room(db, reg.room_id)
    if room.occupied_beds >= room.max_beds:
        _fail(db, 409, "Phòng đã hết chỗ (có đơn khác vừa được duyệt trước)")

    already = db.scalar(
        select(Contract.id).where(
            Contract.student_id == reg.student_id, Contract.status == ContractStatus.ACTIVE
        )
    )
    if already:
        _fail(db, 409, "Sinh viên này đang có hợp đồng còn hiệu lực")

    start = start_date or date.today()
    contract = Contract(
        registration_id=reg.id, student_id=reg.student_id, room_id=room.id,
        start_date=start, end_date=start + timedelta(days=30 * months),
    )
    room.occupied_beds += 1  # an toàn vì đang giữ khóa dòng phòng
    reg.status = RegistrationStatus.APPROVED
    reg.reviewed_by = manager.id
    reg.reviewed_at = datetime.now(timezone.utc)
    db.add(contract)
    try:
        db.commit()  # CHECK ck_room_occupied là chốt chặn cuối cùng ở tầng CSDL
    except IntegrityError:
        _fail(db, 409, "Không thể duyệt do vi phạm ràng buộc dữ liệu")
    db.refresh(reg)
    db.refresh(contract)
    return reg, contract


def reject_registration(db: Session, registration_id: int, manager: User, reason: str) -> Registration:
    reg = _lock_registration(db, registration_id)
    if reg.status != RegistrationStatus.PENDING:
        _fail(db, 409, f"Đơn đã ở trạng thái {reg.status.value}, không thể từ chối")
    reg.status = RegistrationStatus.REJECTED
    reg.reject_reason = reason
    reg.reviewed_by = manager.id
    reg.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reg)
    return reg


def cancel_registration(db: Session, registration_id: int, student: User) -> Registration:
    reg = _lock_registration(db, registration_id)
    if reg.student_id != student.id:
        _fail(db, 403, "Đây không phải đơn của bạn")
    if reg.status != RegistrationStatus.PENDING:
        _fail(db, 409, f"Đơn đã ở trạng thái {reg.status.value}, không thể hủy")
    reg.status = RegistrationStatus.CANCELLED
    db.commit()
    db.refresh(reg)
    return reg


def end_contract(db: Session, contract_id: int) -> Contract:
    contract = db.execute(
        select(Contract).where(Contract.id == contract_id).with_for_update().execution_options(**LOCKED)
    ).scalar_one_or_none()
    if contract is None:
        _fail(db, 404, "Không tìm thấy hợp đồng")
    if contract.status != ContractStatus.ACTIVE:
        _fail(db, 409, "Hợp đồng đã kết thúc")
    room = _lock_room(db, contract.room_id)
    if room.occupied_beds <= 0:
        _fail(db, 409, "Số chỗ đang ở của phòng không hợp lệ")
    contract.status = ContractStatus.ENDED
    room.occupied_beds -= 1
    db.commit()
    db.refresh(contract)
    return contract
