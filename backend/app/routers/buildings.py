from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import STAFF, require_roles
from app.core.errors import DomainError
from app.db.session import get_db
from app.models import Building, Room
from app.models.enums import Role
from app.schemas.building import BuildingCreate, BuildingOut, BuildingUpdate

router = APIRouter()


def _get_or_404(db: Session, building_id: int) -> Building:
    b = db.get(Building, building_id)
    if b is None:
        raise DomainError(404, "Không tìm thấy tòa nhà")
    return b


@router.get("", response_model=list[BuildingOut], summary="Danh sách tòa nhà")
def list_buildings(db: Session = Depends(get_db)):
    return db.scalars(select(Building).order_by(Building.name)).all()


@router.get("/{building_id}", response_model=BuildingOut, summary="Chi tiết tòa nhà")
def get_building(building_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, building_id)


@router.post("", response_model=BuildingOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(*STAFF))], summary="Thêm tòa nhà")
def create_building(data: BuildingCreate, db: Session = Depends(get_db)):
    b = Building(**data.model_dump())
    db.add(b)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Tên tòa nhà đã tồn tại")
    db.refresh(b)
    return b


@router.put("/{building_id}", response_model=BuildingOut,
            dependencies=[Depends(require_roles(*STAFF))], summary="Sửa tòa nhà")
def update_building(building_id: int, data: BuildingUpdate, db: Session = Depends(get_db)):
    b = _get_or_404(db, building_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(b, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "Tên tòa nhà đã tồn tại")
    db.refresh(b)
    return b


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(Role.ADMIN))], summary="Xóa tòa nhà (Admin)")
def delete_building(building_id: int, db: Session = Depends(get_db)):
    b = _get_or_404(db, building_id)
    if db.scalar(select(func.count()).select_from(Room).where(Room.building_id == b.id)):
        raise DomainError(409, "Tòa nhà còn phòng, không thể xóa")
    db.delete(b)
    db.commit()
