# bot/keyboards/kb.py — клавиатуры (inline, single-message навигация)
from __future__ import annotations

from datetime import date, time

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.models import Booking, Master, Service

# Локализация коротких имён дней недели
WEEKDAY_NAMES = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
MONTH_NAMES = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)
MONTH_NAMES_FULL = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def format_date_long(d: date) -> str:
    """Формат даты для текста: «Пн, 17 марта 2026»."""
    return f"{WEEKDAY_NAMES[d.weekday()]}, {d.day} {MONTH_NAMES_FULL[d.month - 1]} {d.year}"


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню: Записаться | Мои записи | О нас."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Записаться", callback_data="book")],
        [InlineKeyboardButton(text="📅 Мои записи", callback_data="my_bookings")],
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
    ])


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    """Выбор услуги. Кнопка: \"{name} — {price:,.0f}₽ ({duration}мин)\" -> svc:{id}. Внизу Главная."""
    rows = [
        [InlineKeyboardButton(
            text=f"{s.name} — {s.price:,.0f}₽ ({s.duration_minutes}мин)",
            callback_data=f"svc:{s.id}",
        )]
        for s in services
    ]
    rows.append([InlineKeyboardButton(text="🏠 Главная", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def masters_kb(
    masters: list[Master], service_id: int
) -> InlineKeyboardMarkup:
    """Выбор мастера. Кнопка \"{name}\" -> mst:{master_id}:{service_id}. Внизу Назад -> book."""
    rows = []
    row: list[InlineKeyboardButton] = []
    for m in masters:
        row.append(InlineKeyboardButton(
            text=m.name,
            callback_data=f"mst:{m.id}:{service_id}",
        ))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="book")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_date(d: date) -> str:
    """Формат даты для кнопки: \"Пн, 17 мар\"."""
    return f"{WEEKDAY_NAMES[d.weekday()]}, {d.day} {MONTH_NAMES[d.month - 1]}"


def dates_kb(
    dates: list[date], master_id: int, service_id: int
) -> InlineKeyboardMarkup:
    """Выбор даты. Кнопка \"Пн, 17 мар\" -> date:{master_id}:{service_id}:{date_iso}. Внизу Назад. По 3 в ряд."""
    rows = []
    row: list[InlineKeyboardButton] = []
    for d in dates:
        row.append(InlineKeyboardButton(
            text=_format_date(d),
            callback_data=f"date:{master_id}:{service_id}:{d.isoformat()}",
        ))
        if len(row) >= 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"svc:{service_id}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(
    slots: list[time],
    master_id: int,
    service_id: int,
    target_date: date,
) -> InlineKeyboardMarkup:
    """Выбор времени. Кнопка \"HH:MM\" -> time:{master_id}:{service_id}:{date_iso}:{time_str}. По 4 в ряд."""
    date_iso = target_date.isoformat()
    rows = []
    row: list[InlineKeyboardButton] = []
    for t in slots:
        time_str = t.strftime("%H:%M")
        row.append(InlineKeyboardButton(
            text=time_str,
            callback_data=f"time:{master_id}:{service_id}:{date_iso}:{time_str}",
        ))
        if len(row) >= 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"date_back:{master_id}:{service_id}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_kb(
    master_id: int,
    service_id: int,
    booking_date: date,
    time_start: time,
) -> InlineKeyboardMarkup:
    """Подтверждение записи. Подтвердить -> confirm_book:... | Отмена -> book."""
    date_str = booking_date.isoformat()
    time_str = time_start.strftime("%H:%M")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_book:{master_id}:{service_id}:{date_str}:{time_str}",
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="book")],
    ])


def my_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    """Мои записи. Кнопка \"📅 {дата} {время} — {услуга}\" -> bk:{booking_id}. Внизу Главная."""
    rows = [
        [InlineKeyboardButton(
            text=f"📅 {b.date.strftime('%d.%m')} {b.time_start.strftime('%H:%M')} — {b.service.name}",
            callback_data=f"bk:{b.id}",
        )]
        for b in bookings
    ]
    rows.append([InlineKeyboardButton(text="🏠 Главная", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def booking_detail_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Детали записи: Отменить запись | Назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отменить запись",
            callback_data=f"cancel_bk:{booking_id}",
        )],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_bookings")],
    ])


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Админ-меню: Статистика | Записи на сегодня | Мастера | Услуги."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📅 Записи на сегодня", callback_data="adm:today")],
        [InlineKeyboardButton(text="👥 Мастера", callback_data="adm:masters")],
        [InlineKeyboardButton(text="💈 Услуги", callback_data="adm:services")],
    ])
