from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, require_roles
from app.db.session import get_db
from app.models import Building, Room, User, UtilityPrice, UtilityReading
from app.models.enums import Role
from app.routers.invoices import invoice_detail
from app.schemas.billing import (PriceCreate, PriceOut, ReadingCreate, ReadingOut,
                                 ReadingWithInvoice)
from app.schemas.common import Page
from app.services import billing_service

router = APIRouter()


def _reading_query():
    return (
        select(UtilityReading, Room.room_number, Building.name)
        .join(Room, Room.id == UtilityReading.room_id)
        .join(Building, Building.id == Room.building_id)
    )


def _to_out(row) -> ReadingOut:
    r, room_number, building_name = row
    return ReadingOut(
        id=r.id, room_id=r.room_id, room_number=room_number, building_name=building_name,
        month=r.month, year=r.year, electric_old=r.electric_old, electric_new=r.electric_new,
        water_old=r.water_old, water_new=r.water_new, recorded_by=r.recorded_by,
        created_at=r.created_at,
    )


@router.post("/readings", response_model=ReadingWithInvoice, status_code=status.HTTP_201_CREATED,
             summary="Ghi chỉ số điện nước tháng và TỰ SINH hóa đơn")
def create_reading(data: ReadingCreate, db: Session = Depends(get_db),
                   staff: User = Depends(require_roles(*STAFF))):
    reading, invoice = billing_service.create_reading_and_invoice(
        db, staff, data.room_id, data.month, data.year, data.electric_new, data.water_new,
        data.electric_old, data.water_old)
    db.expire_all()
    row = db.execute(_reading_query().where(UtilityReading.id == reading.id)).one()
    return ReadingWithInvoice(reading=_to_out(row), invoice=invoice_detail(db, invoice.id))


@router.get("/readings", response_model=Page[ReadingOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Danh sách chỉ số điện nước")
def list_readings(
    room_id: int | None = None, month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None, ge=2000, le=2100),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = []
    if room_id is not None:
        conds.append(UtilityReading.room_id == room_id)
    if month is not None:
        conds.append(UtilityReading.month == month)
    if year is not None:
        conds.append(UtilityReading.year == year)
    total = db.scalar(select(func.count()).select_from(UtilityReading).where(*conds))
    rows = db.execute(_reading_query().where(*conds)
                      .order_by(UtilityReading.year.desc(), UtilityReading.month.desc(), Room.room_number)
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[ReadingOut](items=[_to_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/prices", response_model=list[PriceOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Lịch sử đơn giá điện nước")
def list_prices(db: Session = Depends(get_db)):
    return [PriceOut(id=p.id, electric_per_kwh=p.electric_per_kwh, water_per_m3=p.water_per_m3,
                     effective_from=p.effective_from)
            for p in db.scalars(select(UtilityPrice).order_by(UtilityPrice.effective_from.desc()))]


@router.post("/prices", response_model=PriceOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(Role.ADMIN))], summary="Admin thêm đơn giá mới")
def create_price(data: PriceCreate, db: Session = Depends(get_db)):
    p = UtilityPrice(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return PriceOut(id=p.id, electric_per_kwh=p.electric_per_kwh, water_per_m3=p.water_per_m3,
                    effective_from=p.effective_from)
