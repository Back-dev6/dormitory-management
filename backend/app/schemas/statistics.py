from pydantic import BaseModel

from app.models.enums import Gender


class BuildingOccupancy(BaseModel):
    building_id: int
    building_name: str
    gender_type: Gender
    total_rooms: int
    total_beds: int
    occupied_beds: int
    available_beds: int
    occupancy_rate: float  # phần trăm, 2 chữ số thập phân


class OccupancyReport(BaseModel):
    buildings: list[BuildingOccupancy]
    total_rooms: int
    total_beds: int
    occupied_beds: int
    available_beds: int
    occupancy_rate: float
