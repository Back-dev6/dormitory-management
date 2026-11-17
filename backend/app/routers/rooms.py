from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.core.deps import STAFF, require_roles
from app.core.errors import DomainError
from app.db.session import get_db
from app.models import Building, Contract, Registration, Room
from app.models.enums import ContractStatus, Gender, RegistrationStatus, Role
from app.schemas.common import Page
from app.schemas.room import RoomCreate, RoomOut, RoomUpdate

router = APIRouter()


def to_out(room: Room) -> RoomOut:
    return RoomOut(
        id=room.id, building_id=room.building_id, building_name=room.building.name,
        gender_type=room.building.gender_type, room_number=room.room_number,
        floor=room.floor, max_beds=room.max_beds, occupied_beds=room.occupied_beds,
        available_beds=room.max_beds - room.occupied_beds, price_per_bed=room.price_per_bed,
    )


def _load(db: Session, room_id: int) -> Room:
    room = db.execute(
        select(Room).join(Building, Room.building_id == Building.id)
        .options(contains_eager(Room.building)).where(Room.id == room_id)
    ).scalar_one_or_none()
    if room is None:
        raise DomainError(404, "Không tìm thấy phòng")
    return room


@router.get("", response_model=Page[RoomOut], summary="Danh sách phòng, lọc theo tòa/giá/giới tính/chỗ trống")
def list_rooms(
    building_id: int | None = Query(None, description="Lọc theo tòa"),
    gender: Gender | None = Query(None, description="Lọc theo giới tính của tòa"),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    available_only: bool = Query(False, description="Chỉ phòng còn chỗ"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise DomainError(422, "min_price không được lớn hơn max_price")

    conds = []
    if building_id is not None:
        conds.append(Room.building_id == building_id)
    if gender is not None:
        conds.append(Building.gender_type == gender)
    if min_price is not None:
        conds.append(Room.price_per_bed >= min_price)
    if max_price is not None:
        conds.append(Room.price_per_bed <= max_price)
    if available_only:
        conds.append(Room.occupied_beds < Room.max_beds)

    total = db.scalar(
        select(func.count()).select_from(Room)
        .join(Building, Room.building_id == Building.id).where(*conds)
    )
    rooms = db.execute(
        select(Room).join(Building, Room.building_id == Building.id)
        .options(contains_eager(Room.building)).where(*conds)
        .order_by(Building.name, Room.room_number)
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return Page[RoomOut](items=[to_out(r) for r in rooms], total=total, page=page, page_size=page_size)


@router.get("/{room_id}", response_model=RoomOut, summary="Chi tiết phòng")
def get_room(room_id: int, db: Session = Depends(get_db)):
    return to_out(_load(db, room_id))


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(*STAFF))], summary="Thêm phòng")
def create_room(data: RoomCreate, db: Session = Depends(get_db)):
    if db.get(Building, data.building_id) is None:
        raise DomainError(404, "Không tìm thấy tòa nhà")
    room = Room(**data.model_dump(), occupied_beds=0)
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Số phòng đã tồn tại trong tòa này")
    return to_out(_load(db, room.id))


@router.put("/{room_id}", response_model=RoomOut,
            dependencies=[Depends(require_roles(*STAFF))], summary="Sửa phòng")
def update_room(room_id: int, data: RoomUpdate, db: Session = Depends(get_db)):
    room = db.execute(select(Room).where(Room.id == room_id).with_for_update()).scalar_one_or_none()
    if room is None:
        db.rollback()
        raise DomainError(404, "Không tìm thấy phòng")
    changes = data.model_dump(exclude_unset=True)
    if "max_beds" in changes and changes["max_beds"] < room.occupied_beds:
        db.rollback()
        raise DomainError(409, f"Phòng đang có {room.occupied_beds} người ở, không thể giảm số giường xuống thấp hơn")
    for key, value in changes.items():
        setattr(room, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Số phòng đã tồn tại trong tòa này")
    return to_out(_load(db, room_id))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(Role.ADMIN))], summary="Xóa phòng (Admin)")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise DomainError(404, "Không tìm thấy phòng")
    busy = db.scalar(select(func.count()).select_from(Contract)
                     .where(Contract.room_id == room_id, Contract.status == ContractStatus.ACTIVE))
    pending = db.scalar(select(func.count()).select_from(Registration)
                        .where(Registration.room_id == room_id,
                               Registration.status == RegistrationStatus.PENDING))
    if busy or pending:
        raise DomainError(409, "Phòng còn hợp đồng hiệu lực hoặc đơn đang chờ, không thể xóa")
    try:
        db.delete(room)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Phòng đã có dữ liệu liên quan (lịch sử đăng ký, hóa đơn...), không thể xóa")
