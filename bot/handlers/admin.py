# bot/handlers/admin.py — /admin, статистика, записи, мастера, услуги, команды
from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards.kb import admin_menu_kb
from bot.services.db import (
    add_master,
    add_service,
    delete_master,
    delete_service,
    get_all_bookings,
    get_masters,
    get_services,
    get_stats,
    link_master_service,
)
from bot.utils import edit_safe

router = Router()
_config = Config.from_env()


class AdminFilter:
    """Фильтр: только пользователи из ADMIN_IDS."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        return user.id in _config.ADMIN_IDS


admin_only = AdminFilter()


# --- /admin ---


@router.message(Command("admin"), admin_only)
async def cmd_admin(message: Message, session) -> None:
    """Админ-панель: приветствие и меню."""
    text = f"🔧 <b>Админ-панель — {_config.BUSINESS_NAME}</b>"
    sent = await message.answer(text, reply_markup=admin_menu_kb())
    # Можно сохранить sent.message_id в FSM при необходимости


# --- adm:menu — возврат в меню админки ---


@router.callback_query(F.data == "adm:menu", admin_only)
async def cb_adm_menu(callback: CallbackQuery) -> None:
    """Вернуться в меню админки."""
    text = f"🔧 <b>Админ-панель — {_config.BUSINESS_NAME}</b>"
    await edit_safe(callback.message, text, reply_markup=admin_menu_kb())
    await callback.answer()


# --- Статистика ---


@router.callback_query(F.data == "adm:stats", admin_only)
async def cb_adm_stats(callback: CallbackQuery, session) -> None:
    """Статистика: клиенты, записи, выручка."""
    stats = await get_stats(session)
    revenue = stats["revenue_month"]
    rev_str = f"{revenue:,.0f}".replace(",", " ")
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Клиентов: {stats['users']}\n"
        f"📋 Записей всего: {stats['bookings_total']}\n"
        f"📅 Записей сегодня: {stats['bookings_today']}\n"
        f"💰 Выручка за месяц: {rev_str} ₽"
    )
    await edit_safe(callback.message, text, reply_markup=admin_menu_kb())
    await callback.answer()


# --- Записи на сегодня ---


@router.callback_query(F.data == "adm:today", admin_only)
async def cb_adm_today(callback: CallbackQuery, session) -> None:
    """Список записей на сегодня."""
    today = date.today()
    bookings = await get_all_bookings(
        session, date_filter=today, status=None
    )
    bookings = [b for b in bookings if b.status != "cancelled"]
    if not bookings:
        text = "📅 <b>Записи на сегодня:</b>\n\nСегодня записей нет."
    else:
        lines = [
            f"🕐 {b.time_start.strftime('%H:%M')} — {b.service.name} "
            f"({b.master.name}) → {b.user.full_name}"
            for b in bookings
        ]
        text = "📅 <b>Записи на сегодня:</b>\n\n" + "\n".join(lines)
    await edit_safe(callback.message, text, reply_markup=admin_menu_kb())
    await callback.answer()


# --- Мастера ---


@router.callback_query(F.data == "adm:masters", admin_only)
async def cb_adm_masters(callback: CallbackQuery, session) -> None:
    """Список мастеров и подсказки по командам."""
    masters = await get_masters(session)
    if not masters:
        body = "Нет мастеров."
    else:
        lines = [
            f"{i}. {m.name} — {m.specialization or '—'} ✅"
            for i, m in enumerate(masters, 1)
        ]
        body = "\n".join(lines)
    text = (
        "👥 <b>Мастера:</b>\n\n"
        f"{body}\n\n"
        "Подсказка: /add_master Имя Специализация | /del_master ID"
    )
    await edit_safe(callback.message, text, reply_markup=admin_menu_kb())
    await callback.answer()


# --- Услуги ---


@router.callback_query(F.data == "adm:services", admin_only)
async def cb_adm_services(callback: CallbackQuery, session) -> None:
    """Список услуг и подсказки по командам."""
    services = await get_services(session)
    if not services:
        body = "Нет услуг."
    else:
        lines = [
            f"{i}. {s.name} — {s.price:,.0f} ₽ ({s.duration_minutes} мин)"
            for i, s in enumerate(services, 1)
        ]
        body = "\n".join(lines)
    text = (
        "💈 <b>Услуги:</b>\n\n"
        f"{body}\n\n"
        "Подсказка: /add_service Название|Минуты|Цена | "
        "/del_service ID | /link Мастер_ID Услуга_ID"
    )
    await edit_safe(callback.message, text, reply_markup=admin_menu_kb())
    await callback.answer()


# --- Команды добавления/удаления ---


@router.message(Command("add_master"), admin_only)
async def cmd_add_master(message: Message, session) -> None:
    """Добавить мастера: /add_master Имя Специализация."""
    args = message.text and message.text.split(maxsplit=2)[1:] or []
    if len(args) < 1:
        await message.answer("Использование: /add_master Имя Специализация")
        return
    name = args[0]
    specialization = args[1] if len(args) > 1 else None
    await add_master(session, name, specialization)
    await message.answer("✅ Мастер добавлен")


@router.message(Command("del_master"), admin_only)
async def cmd_del_master(message: Message, session) -> None:
    """Удалить (деактивировать) мастера: /del_master ID."""
    args = message.text and message.text.split()[1:] or []
    if len(args) < 1:
        await message.answer("Использование: /del_master ID")
        return
    try:
        master_id = int(args[0])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    await delete_master(session, master_id)
    await message.answer("✅ Мастер удалён")


@router.message(Command("add_service"), admin_only)
async def cmd_add_service(message: Message, session) -> None:
    """Добавить услугу: /add_service Название|Минуты|Цена."""
    args = message.text and message.text.split(maxsplit=1)[1:] or []
    if len(args) < 1:
        await message.answer(
            "Использование: /add_service Название|Минуты|Цена"
        )
        return
    parts = args[0].split("|")
    if len(parts) != 3:
        await message.answer(
            "Формат: Название|Минуты|Цена (например: Стрижка|45|1500)"
        )
        return
    name = parts[0].strip()
    try:
        duration = int(parts[1].strip())
        price = float(parts[2].strip().replace(",", "."))
    except ValueError:
        await message.answer("Минуты и цена должны быть числами")
        return
    await add_service(session, name, duration, price)
    await message.answer("✅ Услуга добавлена")


@router.message(Command("del_service"), admin_only)
async def cmd_del_service(message: Message, session) -> None:
    """Удалить (деактивировать) услугу: /del_service ID."""
    args = message.text and message.text.split()[1:] or []
    if len(args) < 1:
        await message.answer("Использование: /del_service ID")
        return
    try:
        service_id = int(args[0])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    await delete_service(session, service_id)
    await message.answer("✅ Услуга удалена")


@router.message(Command("link"), admin_only)
async def cmd_link(message: Message, session) -> None:
    """Связать мастера и услугу: /link Мастер_ID Услуга_ID."""
    args = message.text and message.text.split()[1:] or []
    if len(args) < 2:
        await message.answer("Использование: /link Мастер_ID Услуга_ID")
        return
    try:
        master_id = int(args[0])
        service_id = int(args[1])
    except ValueError:
        await message.answer("ID должны быть числами")
        return
    await link_master_service(session, master_id, service_id)
    await message.answer("✅ Связь мастер–услуга добавлена")
