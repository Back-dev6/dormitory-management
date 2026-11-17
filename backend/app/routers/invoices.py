from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, get_current_user, require_roles
from app.core.errors import DomainError
from app.db.session import get_db
from app.models import Building, Contract, Invoice, Room, User, UtilityReading
from app.models.enums import InvoiceStatus, Role
from app.schemas.billing import InvoiceOut
from app.schemas.common import Page
from app.services.excel_service import XLSX_MEDIA_TYPE, invoices_to_xlsx

router = APIRouter()


def _query():
    return (
        select(Invoice, UtilityReading, Room.room_number, Building.name)
        .join(UtilityReading, UtilityReading.id == Invoice.reading_id)
        .join(Room, Room.id == Invoice.room_id)
        .join(Building, Building.id == Room.building_id)
    )


def _to_out(row) -> InvoiceOut:
    inv, rd, room_number, building_name = row
    return InvoiceOut(
        id=inv.id, room_id=inv.room_id, room_number=room_number, building_name=building_name,
        month=rd.month, year=rd.year,
        electric_old=rd.electric_old, electric_new=rd.electric_new,
        electric_usage=rd.electric_new - rd.electric_old,
        water_old=rd.water_old, water_new=rd.water_new, water_usage=rd.water_new - rd.water_old,
        room_fee=inv.room_fee, electric_amount=inv.electric_amount, water_amount=inv.water_amount,
        total=inv.total, status=inv.status, due_date=inv.due_date, paid_at=inv.paid_at,
        created_at=inv.created_at,
    )


def invoice_detail(db: Session, invoice_id: int) -> InvoiceOut:
    db.expire_all()
    return _to_out(db.execute(_query().where(Invoice.id == invoice_id)).one())


def _mine(student_id: int):
    """Hóa đơn của phòng mà sinh viên có hợp đồng, trong kỳ trùng với thời hạn hợp đồng."""
    first_day = func.make_date(UtilityReading.year, UtilityReading.month, 1)
    next_month = first_day + func.make_interval(0, 1)
    return exists().where(
        Contract.student_id == student_id, Contract.room_id == Invoice.room_id,
        first_day <= Contract.end_date, next_month > Contract.start_date,
    )


def _filters(month, year, building_id, status_filter):
    conds = []
    if month is not None:
        conds.append(UtilityReading.month == month)
    if year is not None:
        conds.append(UtilityReading.year == year)
    if building_id is not None:
        conds.append(Building.id == building_id)
    if status_filter is not None:
        conds.append(Invoice.status == status_filter)
    return conds


@router.get("/me", response_model=list[InvoiceOut], summary="Hóa đơn của phòng tôi đang/đã ở")
def my_invoices(db: Session = Depends(get_db), student: User = Depends(require_roles(Role.STUDENT))):
    rows = db.execute(
        _query().where(_mine(student.id)).order_by(UtilityReading.year.desc(), UtilityReading.month.desc())
    ).all()
    return [_to_out(r) for r in rows]


@router.get("/export", summary="Xuất danh sách hóa đơn ra Excel (.xlsx)",
            dependencies=[Depends(require_roles(*STAFF))])
def export_invoices(
    month: int | None = Query(None, ge=1, le=12), year: int | None = Query(None, ge=2000, le=2100),
    building_id: int | None = None,
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        _query().where(*_filters(month, year, building_id, status_filter))
        .order_by(UtilityReading.year, UtilityReading.month, Building.name, Room.room_number)
    ).all()
    data = invoices_to_xlsx([_to_out(r) for r in rows])
    name = f"hoadon_{year or 'tatca'}_{month or 'tatca'}.xlsx"
    return Response(content=data, media_type=XLSX_MEDIA_TYPE,
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("", response_model=Page[InvoiceOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Cán bộ xem danh sách hóa đơn")
def list_invoices(
    month: int | None = Query(None, ge=1, le=12), year: int | None = Query(None, ge=2000, le=2100),
    building_id: int | None = None,
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = _filters(month, year, building_id, status_filter)
    total = db.scalar(
        select(func.count()).select_from(Invoice)
        .join(UtilityReading, UtilityReading.id == Invoice.reading_id)
        .join(Room, Room.id == Invoice.room_id)
        .join(Building, Building.id == Room.building_id).where(*conds)
    )
    rows = db.execute(
        _query().where(*conds)
        .order_by(UtilityReading.year.desc(), UtilityReading.month.desc(), Building.name, Room.room_number)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[InvoiceOut](items=[_to_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/{invoice_id}", response_model=InvoiceOut, summary="Chi tiết hóa đơn")
def get_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = _query().where(Invoice.id == invoice_id)
    if user.role == Role.STUDENT:
        # sinh viên chỉ xem được hóa đơn của chính phòng mình
        if db.execute(stmt).first() is not None and db.execute(stmt.where(_mine(user.id))).first() is None:
            raise DomainError(403, "Đây không phải hóa đơn của phòng bạn")
    row = db.execute(stmt).first()
    if row is None:
        raise DomainError(404, "Không tìm thấy hóa đơn")
    return _to_out(row)


@router.post("/{invoice_id}/pay", response_model=InvoiceOut, dependencies=[Depends(require_roles(*STAFF))],
             summary="Cán bộ đánh dấu hóa đơn đã thanh toán")
def pay_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update()
                     .execution_options(populate_existing=True)).scalar_one_or_none()
    if inv is None:
        db.rollback()
        raise DomainError(404, "Không tìm thấy hóa đơn")
    if inv.status == InvoiceStatus.PAID:
        db.rollback()
        raise DomainError(409, "Hóa đơn đã được thanh toán")
    inv.status = InvoiceStatus.PAID
    inv.paid_at = datetime.now(timezone.utc)
    db.commit()
    return invoice_detail(db, invoice_id)
