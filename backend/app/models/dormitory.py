from decimal import Decimal

from sqlalchemy import (CheckConstraint, Enum, ForeignKey, Integer, Numeric,
                        String, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Gender


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"
    __table_args__ = (CheckConstraint("floors > 0", name="ck_building_floors"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    gender_type: Mapped[Gender] = mapped_column(Enum(Gender, name="gender"))
    address: Mapped[str | None] = mapped_column(String(255))
    floors: Mapped[int] = mapped_column(Integer)

    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("building_id", "room_number", name="uq_room_building_number"),
        CheckConstraint("max_beds > 0", name="ck_room_max_beds"),
        CheckConstraint(
            "occupied_beds >= 0 AND occupied_beds <= max_beds", name="ck_room_occupied"
        ),
        CheckConstraint("price_per_bed >= 0", name="ck_room_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), index=True)
    room_number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(Integer)
    max_beds: Mapped[int] = mapped_column(Integer)
    occupied_beds: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    price_per_bed: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    building: Mapped["Building"] = relationship(back_populates="rooms")
