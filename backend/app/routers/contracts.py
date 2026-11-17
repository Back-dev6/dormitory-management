from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, require_roles
from app.db.session import get_db
from app.models import Building, Contract, Room, User
from app.models.enums import ContractStatus, Role
from app.schemas.common import Page
from app.schemas.registration import ContractOut
from app.services import registration_service as svc

router = APIRouter()


def _query():
    return (
        select(Contract, User.full_name, Room.room_number, Building.name)
        .join(User, User.id == Contract.student_id)
        .join(Room, Room.id == Contract.room_id)
        .join(Building, Building.id == Room.building_id)
    )


def _to_out(row) -> ContractOut:
    c, student_name, room_number, building_name = row
    return ContractOut(
        id=c.id, registration_id=c.registration_id, student_id=c.student_id,
        student_name=student_name, room_id=c.room_id, room_number=room_number,
        building_name=building_name, start_date=c.start_date, end_date=c.end_date,
        status=c.status,
    )


def contract_detail(db: Session, contract_id: int) -> ContractOut:
    db.expire_all()
    return _to_out(db.execute(_query().where(Contract.id == contract_id)).one())


@router.get("/me", response_model=list[ContractOut], summary="Hợp đồng của tôi")
def my_contracts(db: Session = Depends(get_db), student: User = Depends(require_roles(Role.STUDENT))):
    rows = db.execute(_query().where(Contract.student_id == student.id)
                      .order_by(Contract.id.desc())).all()
    return [_to_out(r) for r in rows]


@router.get("", response_model=Page[ContractOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Cán bộ xem danh sách hợp đồng")
def list_contracts(
    status_filter: ContractStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = [Contract.status == status_filter] if status_filter else []
    total = db.scalar(select(func.count()).select_from(Contract).where(*conds))
    rows = db.execute(_query().where(*conds).order_by(Contract.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[ContractOut](items=[_to_out(r) for r in rows], total=total,
                             page=page, page_size=page_size)


@router.post("/{contract_id}/end", response_model=ContractOut,
             dependencies=[Depends(require_roles(*STAFF))], summary="Kết thúc hợp đồng (trả giường)")
def end_contract(contract_id: int, db: Session = Depends(get_db)):
    svc.end_contract(db, contract_id)
    return contract_detail(db, contract_id)
