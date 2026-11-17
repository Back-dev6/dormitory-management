from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, get_current_user, require_roles
from app.core.errors import DomainError
from app.db.session import get_db
from app.models import Building, Contract, Incident, Room, User
from app.models.enums import ContractStatus, IncidentStatus, Role
from app.schemas.common import Page
from app.schemas.incident import IncidentOut, IncidentStatusUpdate
from app.services import storage_service

router = APIRouter()

# Trạng thái chỉ đi tiến: OPEN -> IN_PROGRESS -> RESOLVED
ALLOWED = {
    IncidentStatus.OPEN: {IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED},
    IncidentStatus.IN_PROGRESS: {IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: set(),
}


def _query():
    return (
        select(Incident, User.full_name, User.student_code, Room.room_number, Building.name)
        .join(User, User.id == Incident.student_id)
        .join(Room, Room.id == Incident.room_id)
        .join(Building, Building.id == Room.building_id)
    )


def _to_out(row) -> IncidentOut:
    inc, student_name, student_code, room_number, building_name = row
    return IncidentOut(
        id=inc.id, student_id=inc.student_id, student_name=student_name, student_code=student_code,
        room_id=inc.room_id, room_number=room_number, building_name=building_name,
        title=inc.title, description=inc.description,
        image_url=f"/api/incidents/{inc.id}/image" if inc.image_path else None,
        status=inc.status, handled_by=inc.handled_by, created_at=inc.created_at,
        updated_at=inc.updated_at,
    )


def _detail(db: Session, incident_id: int) -> IncidentOut:
    db.expire_all()
    return _to_out(db.execute(_query().where(Incident.id == incident_id)).one())


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED,
             summary="Sinh viên gửi phản ánh sự cố (kèm ảnh, multipart/form-data)")
def create_incident(
    title: str = Form(min_length=3, max_length=200),
    description: str = Form(min_length=3, max_length=2000),
    image: UploadFile | None = File(None, description="Ảnh JPEG/PNG/WEBP, tối đa 5 MB"),
    db: Session = Depends(get_db),
    student: User = Depends(require_roles(Role.STUDENT)),
):
    contract = db.scalar(select(Contract).where(
        Contract.student_id == student.id, Contract.status == ContractStatus.ACTIVE))
    if contract is None:
        raise DomainError(409, "Bạn chưa có hợp đồng nên chưa thể gửi phản ánh sự cố")
    image_path = storage_service.save_incident_image(image) if image is not None and image.filename else None
    inc = Incident(student_id=student.id, room_id=contract.room_id, title=title.strip(),
                   description=description.strip(), image_path=image_path)
    db.add(inc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage_service.delete(image_path)  # không để lại ảnh mồ côi
        raise
    return _detail(db, inc.id)


@router.get("/me", response_model=list[IncidentOut], summary="Sự cố tôi đã gửi")
def my_incidents(db: Session = Depends(get_db), student: User = Depends(require_roles(Role.STUDENT))):
    rows = db.execute(_query().where(Incident.student_id == student.id)
                      .order_by(Incident.id.desc())).all()
    return [_to_out(r) for r in rows]


@router.get("", response_model=Page[IncidentOut], dependencies=[Depends(require_roles(*STAFF))],
            summary="Cán bộ xem danh sách sự cố")
def list_incidents(
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    building_id: int | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conds = []
    if status_filter is not None:
        conds.append(Incident.status == status_filter)
    if building_id is not None:
        conds.append(Building.id == building_id)
    total = db.scalar(
        select(func.count()).select_from(Incident)
        .join(Room, Room.id == Incident.room_id)
        .join(Building, Building.id == Room.building_id).where(*conds))
    rows = db.execute(_query().where(*conds).order_by(Incident.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[IncidentOut](items=[_to_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.patch("/{incident_id}/status", response_model=IncidentOut, summary="Cán bộ cập nhật trạng thái xử lý")
def update_status(incident_id: int, data: IncidentStatusUpdate, db: Session = Depends(get_db),
                  staff: User = Depends(require_roles(*STAFF))):
    inc = db.execute(select(Incident).where(Incident.id == incident_id).with_for_update()
                     .execution_options(populate_existing=True)).scalar_one_or_none()
    if inc is None:
        db.rollback()
        raise DomainError(404, "Không tìm thấy sự cố")
    if data.status not in ALLOWED[inc.status]:
        current = inc.status.value
        db.rollback()
        raise DomainError(409, f"Không thể chuyển từ {current} sang {data.status.value}")
    inc.status = data.status
    inc.handled_by = staff.id
    db.commit()
    return _detail(db, incident_id)


@router.get("/{incident_id}/image", summary="Xem ảnh sự cố (chủ đơn hoặc cán bộ)")
def get_image(incident_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inc = db.get(Incident, incident_id)
    if inc is None or not inc.image_path:
        raise DomainError(404, "Sự cố không có ảnh")
    if user.role == Role.STUDENT and inc.student_id != user.id:
        raise DomainError(403, "Bạn không có quyền xem ảnh này")
    path = storage_service.resolve(inc.image_path)
    if not path.is_file():
        raise DomainError(404, "Không tìm thấy file ảnh")
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff",
                                       "Cache-Control": "no-store"})
