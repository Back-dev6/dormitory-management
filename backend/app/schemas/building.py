from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Gender


class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gender_type: Gender
    address: str | None = Field(default=None, max_length=255)
    floors: int = Field(gt=0, le=100)


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    gender_type: Gender | None = None
    address: str | None = Field(default=None, max_length=255)
    floors: int | None = Field(default=None, gt=0, le=100)


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gender_type: Gender
    address: str | None
    floors: int
