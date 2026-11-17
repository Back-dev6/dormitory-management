from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import Gender


class RoomCreate(BaseModel):
    building_id: int
    room_number: str = Field(min_length=1, max_length=20)
    floor: int = Field(ge=1, le=100)
    max_beds: int = Field(gt=0, le=20)
    price_per_bed: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class RoomUpdate(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=20)
    floor: int | None = Field(default=None, ge=1, le=100)
    max_beds: int | None = Field(default=None, gt=0, le=20)
    price_per_bed: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class RoomOut(BaseModel):
    id: int
    building_id: int
    building_name: str
    gender_type: Gender
    room_number: str
    floor: int
    max_beds: int
    occupied_beds: int
    available_beds: int
    price_per_bed: Decimal
