from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, Date, DateTime, Enum, ForeignKey,
                        Integer, Numeric, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import InvoiceStatus


class UtilityPrice(Base, TimestampMixin):
    __tablename__ = "utility_prices"
    __table_args__ = (
        CheckConstraint("electric_per_kwh >= 0 AND water_per_m3 >= 0", name="ck_price_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    electric_per_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    water_per_m3: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    effective_from: Mapped[date] = mapped_column(Date)


class UtilityReading(Base, TimestampMixin):
    __tablename__ = "utility_readings"
    __table_args__ = (
        UniqueConstraint("room_id", "month", "year", name="uq_reading_room_month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_reading_month"),
        CheckConstraint("electric_old >= 0 AND water_old >= 0", name="ck_reading_old"),
        CheckConstraint(
            "electric_new >= electric_old AND water_new >= water_old", name="ck_reading_new"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    month: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)
    electric_old: Mapped[int] = mapped_column(Integer)
    electric_new: Mapped[int] = mapped_column(Integer)
    water_old: Mapped[int] = mapped_column(Integer)
    water_new: Mapped[int] = mapped_column(Integer)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "room_fee >= 0 AND electric_amount >= 0 AND water_amount >= 0 AND total >= 0",
            name="ck_invoice_amounts",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("utility_readings.id"), unique=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    room_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    electric_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    water_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.UNPAID,
        server_default=InvoiceStatus.UNPAID.name,
    )
    due_date: Mapped[date] = mapped_column(Date)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
