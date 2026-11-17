from datetime import date, datetime

from sqlalchemy import (CheckConstraint, Date, DateTime, Enum, ForeignKey, Index,
                        Integer, String, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ContractStatus, RegistrationStatus


class Registration(Base, TimestampMixin):
    __tablename__ = "registrations"
    __table_args__ = (
        # Mỗi sinh viên chỉ có tối đa 1 đơn đang chờ duyệt
        Index(
            "uq_one_pending_per_student", "student_id",
            unique=True, postgresql_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status"),
        default=RegistrationStatus.PENDING,
        server_default=RegistrationStatus.PENDING.name,
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(String(255))


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_contract_dates"),
        # Mỗi sinh viên chỉ có tối đa 1 hợp đồng đang hiệu lực
        Index(
            "uq_one_active_contract_per_student", "student_id",
            unique=True, postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("registrations.id"), unique=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"),
        default=ContractStatus.ACTIVE,
        server_default=ContractStatus.ACTIVE.name,
    )
