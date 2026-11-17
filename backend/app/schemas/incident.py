from datetime import datetime

from pydantic import BaseModel

from app.models.enums import IncidentStatus


class IncidentOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_code: str | None
    room_id: int
    room_number: str
    building_name: str
    title: str
    description: str
    image_url: str | None
    status: IncidentStatus
    handled_by: int | None
    created_at: datetime
    updated_at: datetime


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
