from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import InvoiceStatus


class ReadingCreate(BaseModel):
    room_id: int
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    electric_new: int = Field(ge=0, description="Chỉ số điện mới (kWh)")
    water_new: int = Field(ge=0, description="Chỉ số nước mới (m3)")
    electric_old: int | None = Field(default=None, ge=0,
                                     description="Chỉ cần khi phòng CHƯA có chỉ số nào (mặc định 0)")
    water_old: int | None = Field(default=None, ge=0, description="Như trên")


class ReadingOut(BaseModel):
    id: int
    room_id: int
    room_number: str
    building_name: str
    month: int
    year: int
    electric_old: int
    electric_new: int
    water_old: int
    water_new: int
    recorded_by: int
    created_at: datetime


class PriceCreate(BaseModel):
    electric_per_kwh: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    water_per_m3: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    effective_from: date


class PriceOut(BaseModel):
    id: int
    electric_per_kwh: Decimal
    water_per_m3: Decimal
    effective_from: date


class InvoiceOut(BaseModel):
    id: int
    room_id: int
    room_number: str
    building_name: str
    month: int
    year: int
    electric_old: int
    electric_new: int
    electric_usage: int
    water_old: int
    water_new: int
    water_usage: int
    room_fee: Decimal
    electric_amount: Decimal
    water_amount: Decimal
    total: Decimal
    status: InvoiceStatus
    due_date: date
    paid_at: datetime | None
    created_at: datetime


class ReadingWithInvoice(BaseModel):
    reading: ReadingOut
    invoice: InvoiceOut
