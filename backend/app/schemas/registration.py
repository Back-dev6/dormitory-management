from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import ContractStatus, RegistrationStatus


class RegistrationCreate(BaseModel):
    room_id: int


class RegistrationApprove(BaseModel):
    start_date: date | None = Field(default=None, description="Mặc định: hôm nay")
    months: int = Field(default=6, ge=1, le=24, description="Thời hạn hợp đồng (tháng)")


class RegistrationReject(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class RegistrationOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_code: str | None
    room_id: int
    room_number: str
    building_name: str
    status: RegistrationStatus
    reviewed_by: int | None
    reviewed_at: datetime | None
    reject_reason: str | None
    created_at: datetime


class ContractOut(BaseModel):
    id: int
    registration_id: int
    student_id: int
    student_name: str
    room_id: int
    room_number: str
    building_name: str
    start_date: date
    end_date: date
    status: ContractStatus


class ApproveOut(BaseModel):
    registration: RegistrationOut
    contract: ContractOut
