# bot/models/models.py — сущности БД (SQLAlchemy 2.0, async)
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.database import Base

if TYPE_CHECKING:
    pass


class Master(Base):
    """Мастер/специалист."""

    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    services: Mapped[list[Service]] = relationship(
        "Service",
        secondary="master_services",
        back_populates="masters",
        lazy="selectin",
    )
    bookings: Mapped[list[Booking]] = relationship(
        "Booking",
        back_populates="master",
        lazy="selectin",
    )
    work_schedules: Mapped[list[WorkSchedule]] = relationship(
        "WorkSchedule",
        back_populates="master",
        lazy="selectin",
    )


class Service(Base):
    """Услуга."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    masters: Mapped[list[Master]] = relationship(
        "Master",
        secondary="master_services",
        back_populates="services",
        lazy="selectin",
    )
    bookings: Mapped[list[Booking]] = relationship(
        "Booking",
        back_populates="service",
        lazy="selectin",
    )


class MasterService(Base):
    """Связь мастер — услуга (many-to-many)."""

    __tablename__ = "master_services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)

    master: Mapped[Master] = relationship(
        "Master", lazy="selectin", overlaps="masters,services"
    )
    service: Mapped[Service] = relationship(
        "Service", lazy="selectin", overlaps="masters,services"
    )


class User(Base):
    """Клиент (пользователь бота)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    full_name: Mapped[str] = mapped_column(nullable=False)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings: Mapped[list[Booking]] = relationship(
        "Booking",
        back_populates="user",
        lazy="selectin",
    )


class Booking(Base):
    """Запись на приём."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_start: Mapped[time] = mapped_column(Time, nullable=False)
    time_end: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="bookings", lazy="selectin")
    master: Mapped[Master] = relationship(
        "Master", back_populates="bookings", lazy="selectin"
    )
    service: Mapped[Service] = relationship(
        "Service", back_populates="bookings", lazy="selectin"
    )


class WorkSchedule(Base):
    """Рабочий график мастера по дням недели (0=Пн ... 6=Вс)."""

    __tablename__ = "work_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_working: Mapped[bool] = mapped_column(default=True, nullable=False)

    master: Mapped[Master] = relationship(
        "Master", back_populates="work_schedules", lazy="selectin"
    )
