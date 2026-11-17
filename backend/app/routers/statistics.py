from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import STAFF, require_roles
from app.db.session import get_db
from app.models import Building, Room
from app.schemas.statistics import BuildingOccupancy, OccupancyReport
from app.services.excel_service import XLSX_MEDIA_TYPE, occupancy_to_xlsx

router = APIRouter(dependencies=[Depends(require_roles(*STAFF))])


def _rate(occupied: int, total: int) -> float:
    return round(occupied * 100 / total, 2) if total else 0.0


def build_report(db: Session) -> OccupancyReport:
    rows = db.execute(
        select(Building.id, Building.name, Building.gender_type, func.count(Room.id),
               func.coalesce(func.sum(Room.max_beds), 0), func.coalesce(func.sum(Room.occupied_beds), 0))
        .outerjoin(Room, Room.building_id == Building.id)
        .group_by(Building.id).order_by(Building.name)
    ).all()
    items = [BuildingOccupancy(
        building_id=r[0], building_name=r[1], gender_type=r[2], total_rooms=r[3],
        total_beds=int(r[4]), occupied_beds=int(r[5]), available_beds=int(r[4]) - int(r[5]),
        occupancy_rate=_rate(int(r[5]), int(r[4]))) for r in rows]
    beds, occ = sum(i.total_beds for i in items), sum(i.occupied_beds for i in items)
    return OccupancyReport(buildings=items, total_rooms=sum(i.total_rooms for i in items),
                           total_beds=beds, occupied_beds=occ, available_beds=beds - occ,
                           occupancy_rate=_rate(occ, beds))


@router.get("/occupancy", response_model=OccupancyReport, summary="Tỷ lệ lấp đầy giường theo từng tòa")
def occupancy(db: Session = Depends(get_db)):
    return build_report(db)


@router.get("/occupancy/export", summary="Xuất báo cáo tỷ lệ lấp đầy ra Excel")
def export_occupancy(db: Session = Depends(get_db)):
    return Response(content=occupancy_to_xlsx(build_report(db)), media_type=XLSX_MEDIA_TYPE,
                    headers={"Content-Disposition": 'attachment; filename="tyle_lapday.xlsx"'})
