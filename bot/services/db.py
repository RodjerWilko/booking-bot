# bot/services/db.py — CRUD и бизнес-логика (пользователи, мастера, услуги, записи)
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.models import (
    Booking,
    Master,
    MasterService,
    Service,
    User,
    WorkSchedule,
)

logger = logging.getLogger(__name__)

# --- Пользователи ---


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str,
) -> User:
    """Получить или создать пользователя по telegram_id."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name or "Клиент",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# --- Мастера ---


async def get_masters(session: AsyncSession) -> list[Master]:
    """Все активные мастера."""
    result = await session.execute(
        select(Master).where(Master.is_active.is_(True)).order_by(Master.name)
    )
    return list(result.scalars().all())


async def get_master(session: AsyncSession, master_id: int) -> Master | None:
    """Мастер по id."""
    result = await session.execute(select(Master).where(Master.id == master_id))
    return result.scalar_one_or_none()


async def get_masters_for_service(
    session: AsyncSession, service_id: int
) -> list[Master]:
    """Мастера, оказывающие данную услугу (активные)."""
    result = await session.execute(
        select(Master)
        .join(MasterService, MasterService.master_id == Master.id)
        .where(
            and_(
                MasterService.service_id == service_id,
                Master.is_active.is_(True),
            )
        )
        .order_by(Master.name)
    )
    return list(result.scalars().unique().all())


async def add_master(
    session: AsyncSession,
    name: str,
    specialization: str | None = None,
) -> Master:
    """Добавить мастера."""
    master = Master(name=name, specialization=specialization)
    session.add(master)
    await session.commit()
    await session.refresh(master)
    return master


async def delete_master(session: AsyncSession, master_id: int) -> None:
    """Удалить мастера (или деактивировать)."""
    result = await session.execute(select(Master).where(Master.id == master_id))
    master = result.scalar_one_or_none()
    if master:
        master.is_active = False
        await session.commit()


# --- Услуги ---


async def get_services(session: AsyncSession) -> list[Service]:
    """Все активные услуги."""
    result = await session.execute(
        select(Service).where(Service.is_active.is_(True)).order_by(Service.name)
    )
    return list(result.scalars().all())


async def get_service(session: AsyncSession, service_id: int) -> Service | None:
    """Услуга по id."""
    result = await session.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def get_services_for_master(
    session: AsyncSession, master_id: int
) -> list[Service]:
    """Услуги, которые оказывает мастер (активные)."""
    result = await session.execute(
        select(Service)
        .join(MasterService, MasterService.service_id == Service.id)
        .where(
            and_(
                MasterService.master_id == master_id,
                Service.is_active.is_(True),
            )
        )
        .order_by(Service.name)
    )
    return list(result.scalars().unique().all())


async def add_service(
    session: AsyncSession,
    name: str,
    duration_minutes: int,
    price: Decimal | int | float,
    description: str = "",
) -> Service:
    """Добавить услугу."""
    price_val = Decimal(str(price))
    service = Service(
        name=name,
        description=description,
        duration_minutes=duration_minutes,
        price=price_val,
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def delete_service(session: AsyncSession, service_id: int) -> None:
    """Удалить услугу (деактивировать)."""
    result = await session.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar_one_or_none()
    if svc:
        svc.is_active = False
        await session.commit()


async def link_master_service(
    session: AsyncSession, master_id: int, service_id: int
) -> None:
    """Связать мастера и услугу."""
    existing = await session.execute(
        select(MasterService).where(
            and_(
                MasterService.master_id == master_id,
                MasterService.service_id == service_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return
    link = MasterService(master_id=master_id, service_id=service_id)
    session.add(link)
    await session.commit()


# --- Расписание мастера ---


async def get_master_schedule(
    session: AsyncSession, master_id: int
) -> list[WorkSchedule]:
    """Рабочий график мастера по дням недели (0=Пн ... 6=Вс)."""
    result = await session.execute(
        select(WorkSchedule)
        .where(WorkSchedule.master_id == master_id)
        .order_by(WorkSchedule.day_of_week)
    )
    return list(result.scalars().all())


async def set_master_schedule(
    session: AsyncSession,
    master_id: int,
    day_of_week: int,
    start_time: time,
    end_time: time,
    is_working: bool = True,
) -> WorkSchedule:
    """Установить слот расписания на день. Создаёт или обновляет запись."""
    result = await session.execute(
        select(WorkSchedule).where(
            and_(
                WorkSchedule.master_id == master_id,
                WorkSchedule.day_of_week == day_of_week,
            )
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.start_time = start_time
        row.end_time = end_time
        row.is_working = is_working
        await session.commit()
        await session.refresh(row)
        return row
    row = WorkSchedule(
        master_id=master_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        is_working=is_working,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


# --- Свободные слоты ---


def _slots_for_interval(
    start: time, end: time, step_minutes: int = 30
) -> list[time]:
    """Генерация слотов с шагом step_minutes в интервале [start, end)."""
    slots: list[time] = []
    td = timedelta(minutes=step_minutes)
    dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    while dt < end_dt:
        slots.append(dt.time())
        dt += td
    return slots


async def get_available_dates(
    session: AsyncSession,
    master_id: int,
    service_id: int,
    days_ahead: int = 14,
) -> list[date]:
    """
    Даты на ближайшие days_ahead дней, где у мастера есть хотя бы один
    свободный слот. Учитываются WorkSchedule и брони (status != cancelled).
    Прошедшие дни и сегодня (если все слоты прошли) не показываются.
    """
    today = date.today()
    service = await get_service(session, service_id)
    if not service:
        return []
    schedule_list = await get_master_schedule(session, master_id)
    schedule_by_day = {s.day_of_week: s for s in schedule_list if s.is_working}
    result_dates: list[date] = []
    for d in range(days_ahead):
        day = today + timedelta(days=d)
        dow = day.weekday()
        if dow not in schedule_by_day:
            continue
        ws = schedule_by_day[dow]
        slots = _slots_for_interval(ws.start_time, ws.end_time)
        if not slots:
            continue
        # Занятые слоты на этот день
        bookings_result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.master_id == master_id,
                    Booking.date == day,
                    Booking.status != "cancelled",
                )
            )
        )
        bookings = list(bookings_result.scalars().all())
        # Заняты слоты, попадающие в интервал любой брони [time_start, time_end)
        occupied = set()
        for b in bookings:
            for t in slots:
                if b.time_start <= t < b.time_end:
                    occupied.add(t)
        now = datetime.now().time() if day == today else None
        free = [
            t
            for t in slots
            if t not in occupied and (now is None or t > now)
        ]
        if free:
            result_dates.append(day)
    return result_dates


async def get_available_slots(
    session: AsyncSession,
    master_id: int,
    service_id: int,
    target_date: date,
) -> list[time]:
    """
    Свободные слоты на дату. Слоты каждые 30 мин в рабочие часы мастера,
    минус занятые (time_start в существующих бронях). Если дата — сегодня,
    убираем прошедшие слоты.
    """
    schedule_list = await get_master_schedule(session, master_id)
    dow = target_date.weekday()
    ws = next((s for s in schedule_list if s.day_of_week == dow and s.is_working), None)
    if not ws:
        return []
    slots = _slots_for_interval(ws.start_time, ws.end_time)
    bookings_result = await session.execute(
        select(Booking).where(
            and_(
                Booking.master_id == master_id,
                Booking.date == target_date,
                Booking.status != "cancelled",
            )
        )
    )
    bookings = list(bookings_result.scalars().all())
    occupied = set()
    for b in bookings:
        for t in slots:
            if b.time_start <= t < b.time_end:
                occupied.add(t)
    today = date.today()
    now = datetime.now().time() if target_date == today else None
    return [
        t
        for t in slots
        if t not in occupied and (now is None or t > now)
    ]


# --- Записи ---


async def create_booking(
    session: AsyncSession,
    telegram_id: int,
    master_id: int,
    service_id: int,
    booking_date: date,
    time_start: time,
) -> Booking:
    """Создать запись. time_end вычисляется из duration услуги."""
    user = await get_or_create_user(session, telegram_id, None, "")
    service = await get_service(session, service_id)
    if not service:
        raise ValueError("Услуга не найдена")
    delta = timedelta(minutes=service.duration_minutes)
    start_dt = datetime.combine(booking_date, time_start)
    end_dt = start_dt + delta
    time_end = end_dt.time()
    booking = Booking(
        user_id=user.id,
        master_id=master_id,
        service_id=service_id,
        date=booking_date,
        time_start=time_start,
        time_end=time_end,
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_user_bookings(
    session: AsyncSession,
    telegram_id: int,
    only_upcoming: bool = True,
) -> list[Booking]:
    """Записи пользователя с мастером и услугой. only_upcoming — только будущие."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return []
    q = (
        select(Booking)
        .where(Booking.user_id == user.id)
        .options(
            selectinload(Booking.master),
            selectinload(Booking.service),
        )
        .order_by(Booking.date, Booking.time_start)
    )
    if only_upcoming:
        today = date.today()
        q = q.where(
            (Booking.date > today)
            | (
                (Booking.date == today)
                & (Booking.time_start >= datetime.now().time())
            )
        )
        q = q.where(Booking.status == "confirmed")
    result = await session.execute(q)
    return list(result.scalars().unique().all())


async def cancel_booking(
    session: AsyncSession, booking_id: int, telegram_id: int
) -> Booking | None:
    """Отменить запись (status=cancelled). Проверяет принадлежность пользователю."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    result = await session.execute(
        select(Booking).where(
            and_(Booking.id == booking_id, Booking.user_id == user.id)
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        return None
    booking.status = "cancelled"
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_upcoming_bookings_for_reminder(
    session: AsyncSession, minutes_before: int
) -> list[Booking]:
    """Записи, до начала которых <= minutes_before минут и reminder_sent=False."""
    now = datetime.now()
    border = now + timedelta(minutes=minutes_before)
    result = await session.execute(
        select(Booking)
        .options(
            selectinload(Booking.master),
            selectinload(Booking.service),
            selectinload(Booking.user),
        )
        .where(Booking.reminder_sent.is_(False))
        .where(Booking.status == "confirmed")
        .where(
            (Booking.date < border.date())
            | (
                (Booking.date == border.date())
                & (Booking.time_start <= border.time())
            )
        )
        .where(
            (Booking.date > now.date())
            | (
                (Booking.date == now.date())
                & (Booking.time_start > now.time())
            )
        )
    )
    return list(result.scalars().unique().all())


async def mark_reminder_sent(session: AsyncSession, booking_id: int) -> None:
    """Пометить напоминание отправленным."""
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    b = result.scalar_one_or_none()
    if b:
        b.reminder_sent = True
        await session.commit()


async def get_all_bookings(
    session: AsyncSession,
    date_filter: date | None = None,
    master_id: int | None = None,
    status: str | None = None,
) -> list[Booking]:
    """Для админки: все записи с опциональными фильтрами."""
    q = (
        select(Booking)
        .options(
            selectinload(Booking.master),
            selectinload(Booking.service),
            selectinload(Booking.user),
        )
        .order_by(Booking.date, Booking.time_start)
    )
    if date_filter is not None:
        q = q.where(Booking.date == date_filter)
    if master_id is not None:
        q = q.where(Booking.master_id == master_id)
    if status is not None:
        q = q.where(Booking.status == status)
    result = await session.execute(q)
    return list(result.scalars().unique().all())


async def get_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    """Запись по id."""
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    return result.scalar_one_or_none()


# --- Статистика ---


async def get_stats(session: AsyncSession) -> dict:
    """Статистика: users, bookings_total, bookings_today, revenue_month."""
    today = date.today()
    month_start = today.replace(day=1)
    users_count = await session.execute(select(func.count(User.id)))
    total_bookings = await session.execute(select(func.count(Booking.id)))
    today_bookings = await session.execute(
        select(func.count(Booking.id)).where(
            and_(Booking.date == today, Booking.status != "cancelled")
        )
    )
    revenue_result = await session.execute(
        select(func.coalesce(func.sum(Service.price), 0))
        .select_from(Booking)
        .join(Service, Service.id == Booking.service_id)
        .where(
            and_(
                Booking.date >= month_start,
                Booking.status.in_(["confirmed", "completed"]),
            )
        )
    )
    return {
        "users": users_count.scalar() or 0,
        "bookings_total": total_bookings.scalar() or 0,
        "bookings_today": today_bookings.scalar() or 0,
        "revenue_month": revenue_result.scalar() or Decimal("0"),
    }


# --- Демо-данные ---


async def seed_demo_data(session: AsyncSession) -> None:
    """Заполнить демо-данные только при пустой таблице мастеров."""
    result = await session.execute(select(Master).limit(1))
    if result.scalar_one_or_none() is not None:
        return
    m1 = Master(name="Алексей", specialization="стрижки", is_active=True)
    m2 = Master(name="Мария", specialization="маникюр", is_active=True)
    m3 = Master(name="Дмитрий", specialization="массаж", is_active=True)
    session.add_all([m1, m2, m3])
    await session.flush()
    s1 = Service(
        name="Мужская стрижка",
        duration_minutes=45,
        price=Decimal("1500"),
        is_active=True,
    )
    s2 = Service(
        name="Детская стрижка",
        duration_minutes=30,
        price=Decimal("800"),
        is_active=True,
    )
    s3 = Service(
        name="Маникюр классический",
        duration_minutes=60,
        price=Decimal("2000"),
        is_active=True,
    )
    s4 = Service(
        name="Маникюр с покрытием",
        duration_minutes=90,
        price=Decimal("3500"),
        is_active=True,
    )
    s5 = Service(
        name="Массаж спины",
        duration_minutes=60,
        price=Decimal("3000"),
        is_active=True,
    )
    s6 = Service(
        name="Массаж общий",
        duration_minutes=90,
        price=Decimal("5000"),
        is_active=True,
    )
    session.add_all([s1, s2, s3, s4, s5, s6])
    await session.flush()
    for mid, sids in [(m1.id, [s1.id, s2.id]), (m2.id, [s3.id, s4.id]), (m3.id, [s5.id, s6.id])]:
        for sid in sids:
            session.add(MasterService(master_id=mid, service_id=sid))
    t10 = time(10, 0)
    t20 = time(20, 0)
    t16 = time(16, 0)
    for master in [m1, m2, m3]:
        for dow in range(5):
            session.add(
                WorkSchedule(
                    master_id=master.id,
                    day_of_week=dow,
                    start_time=t10,
                    end_time=t20,
                    is_working=True,
                )
            )
        session.add(
            WorkSchedule(
                master_id=master.id,
                day_of_week=5,
                start_time=t10,
                end_time=t16,
                is_working=True,
            )
        )
    await session.commit()
    logger.info("Демо-данные созданы.")
