from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, require_roles
from app.db.session import get_db
from app.models import Building, Registration, Room, User
from app.models.enums import RegistrationStatus, Role
from app.schemas.common import Page
from app.schemas.registration import (ApproveOut, RegistrationApprove, RegistrationCreate,
                                      RegistrationOut, RegistrationReject)
from app.services import registration_service as svc
from app.routers.contracts import contract_detail

router = APIRouter()


def _detail_query():
    return (
        select(Registration, User.full_name, User.student_code, Room.room_number, Building.name)
        .join(User, User.id == Registration.student_id)
        .join(Room, Room.id == Registration.room_id)
        .join(Building, Building.id == Room.building_id)
    )


def _to_out(row) -> RegistrationOut:
    reg, student_name, student_code, room_number, building_name = row
    return RegistrationOut(
        id=reg.id, student_id=reg.student_id, student_name=student_name,
        student_code=student_code, room_id=reg.room_id, room_number=room_number,
        building_name=building_name, status=reg.status, reviewed_by=reg.reviewed_by,
        reviewed_at=reg.reviewed_at, reject_reason=reg.reject_reason, created_at=reg.created_at,
    )


def registration_detail(db: Session, registration_id: int) -> RegistrationOut:
    db.expire_all()
    row = db.execute(_detail_query().where(Registration.id == registration_id)).one()
    return _to_out(row)


@router.post("", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED,
             summary="Sinh viên gửi đơn đăng ký phòng")
def create_registration(data: RegistrationCreate, db: Session = Depends(get_db),
                        student: User = Depends(require_roles(Role.STUDENT))):
    reg = svc.create_registration(db, student, data.room_id)
    return registration_detail(db, reg.id)


@router.get("/me", response_model=list[RegistrationOut], summary="Đơn đăng ký của tôi")
def my_registrations(db: Session = Depends(get_db),
                     student: User = Depends(require_roles(Role.STUDENT))):
    rows = db.execute(_detail_query().where(Registration.student_id == student.id)
                      .order_by(Registration.id.desc())).all()
    return [_to_out(r) for r in rows]


@router.get("", response_model=Page[RegistrationOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Cán bộ xem danh sách đơn (lọc theo trạng thái)")
def list_registrations(
    status_filter: RegistrationStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = [Registration.status == status_filter] if status_filter else []
    total = db.scalar(select(func.count()).select_from(Registration).where(*conds))
    rows = db.execute(_detail_query().where(*conds).order_by(Registration.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[RegistrationOut](items=[_to_out(r) for r in rows], total=total,
                                 page=page, page_size=page_size)


@router.post("/{registration_id}/approve", response_model=ApproveOut,
             summary="Cán bộ duyệt đơn (khóa giao dịch, tạo hợp đồng)")
def approve(registration_id: int, data: RegistrationApprove | None = None,
            db: Session = Depends(get_db), manager: User = Depends(require_roles(*STAFF))):
    data = data or RegistrationApprove()
    reg, contract = svc.approve_registration(db, registration_id, manager, data.start_date, data.months)
    return ApproveOut(registration=registration_detail(db, reg.id),
                      contract=contract_detail(db, contract.id))


@router.post("/{registration_id}/reject", response_model=RegistrationOut, summary="Cán bộ từ chối đơn")
def reject(registration_id: int, data: RegistrationReject, db: Session = Depends(get_db),
           manager: User = Depends(require_roles(*STAFF))):
    reg = svc.reject_registration(db, registration_id, manager, data.reason)
    return registration_detail(db, reg.id)


@router.post("/{registration_id}/cancel", response_model=RegistrationOut,
             summary="Sinh viên hủy đơn đang chờ")
def cancel(registration_id: int, db: Session = Depends(get_db),
           student: User = Depends(require_roles(Role.STUDENT))):
    reg = svc.cancel_registration(db, registration_id, student)
    return registration_detail(db, reg.id)
