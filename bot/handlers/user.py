# bot/handlers/user.py — /start, навигация, запись, мои записи (single-message UI)
from __future__ import annotations

from datetime import date, datetime, time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards.kb import (
    booking_detail_kb,
    confirm_booking_kb,
    dates_kb,
    format_date_long,
    main_menu_kb,
    masters_kb,
    my_bookings_kb,
    services_kb,
    times_kb,
)
from bot.services.db import (
    create_booking,
    cancel_booking,
    get_available_dates,
    get_available_slots,
    get_booking,
    get_masters_for_service,
    get_or_create_user,
    get_service,
    get_services,
    get_user_bookings,
    get_master,
)
from bot.utils import edit_safe

router = Router()
_config = Config.from_env()


async def _edit_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактировать сообщение в главное меню и очистить FSM."""
    await state.clear()
    text = (
        f"💈 <b>{_config.BUSINESS_NAME}</b>\n\n"
        "Добро пожаловать! Выберите действие:"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# --- /start ---


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    """Приветствие и главное меню. Сохраняем main_msg_id в FSM."""
    await state.clear()
    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name or "",
    )
    text = (
        f"💈 <b>{_config.BUSINESS_NAME}</b>\n\n"
        "Добро пожаловать! Выберите действие:"
    )
    sent = await message.answer(text, reply_markup=main_menu_kb())
    await state.update_data(main_msg_id=sent.message_id)


# --- Главная и О нас ---


@router.callback_query(F.data == "main")
async def cb_main(callback: CallbackQuery, state: FSMContext) -> None:
    await _edit_to_main(callback, state)


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await _edit_to_main(callback, state)


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery) -> None:
    text = (
        f"ℹ️ <b>О нас</b>\n\n"
        f"💈 {_config.BUSINESS_NAME}\n"
        f"🕐 Режим работы: {_config.WORK_START_HOUR}:00 — {_config.WORK_END_HOUR}:00\n"
        "📞 По вопросам: @R_Willl"
    )
    await edit_safe(callback.message, text, reply_markup=main_menu_kb())
    await callback.answer()


# --- Путь записи ---


@router.callback_query(F.data == "book")
async def cb_book(callback: CallbackQuery, session) -> None:
    """Показать список услуг."""
    services = await get_services(session)
    text = "💈 <b>Выберите услугу:</b>"
    await edit_safe(callback.message, text, reply_markup=services_kb(services))
    await callback.answer()


@router.callback_query(F.data.startswith("svc:"))
async def cb_svc(callback: CallbackQuery, session) -> None:
    """Выбрана услуга — показать мастеров."""
    _, sid = callback.data.split(":", 1)
    service_id = int(sid)
    masters = await get_masters_for_service(session, service_id)
    if not masters:
        await callback.answer("Нет доступных мастеров", show_alert=True)
        return
    service = await get_service(session, service_id)
    name = service.name if service else ""
    text = f"👤 <b>Выберите мастера:</b>\n\nУслуга: {name}"
    await edit_safe(
        callback.message,
        text,
        reply_markup=masters_kb(masters, service_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mst:"))
async def cb_mst(callback: CallbackQuery, session) -> None:
    """Выбран мастер — показать даты."""
    parts = callback.data.split(":")
    master_id, service_id = int(parts[1]), int(parts[2])
    dates = await get_available_dates(session, master_id, service_id, days_ahead=14)
    if not dates:
        await callback.answer(
            "Нет свободных дат на ближайшие 2 недели",
            show_alert=True,
        )
        return
    service = await get_service(session, service_id)
    master = await get_master(session, master_id)
    s_name = service.name if service else ""
    m_name = master.name if master else ""
    text = (
        f"📅 <b>Выберите дату:</b>\n\n"
        f"Услуга: {s_name}\nМастер: {m_name}"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=dates_kb(dates, master_id, service_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date_back:"))
async def cb_date_back(callback: CallbackQuery, session) -> None:
    """Назад к выбору даты (то же, что после выбора мастера)."""
    parts = callback.data.split(":")
    master_id, service_id = int(parts[1]), int(parts[2])
    dates = await get_available_dates(session, master_id, service_id, days_ahead=14)
    if not dates:
        await callback.answer("Нет свободных дат", show_alert=True)
        return
    service = await get_service(session, service_id)
    master = await get_master(session, master_id)
    s_name = service.name if service else ""
    m_name = master.name if master else ""
    text = (
        f"📅 <b>Выберите дату:</b>\n\n"
        f"Услуга: {s_name}\nМастер: {m_name}"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=dates_kb(dates, master_id, service_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date:"))
async def cb_date(callback: CallbackQuery, session) -> None:
    """Выбрана дата — показать слоты времени."""
    parts = callback.data.split(":")
    master_id, service_id = int(parts[1]), int(parts[2])
    date_iso = parts[3]
    target_date = date.fromisoformat(date_iso)
    slots = await get_available_slots(session, master_id, service_id, target_date)
    if not slots:
        await callback.answer("На эту дату нет свободного времени", show_alert=True)
        return
    service = await get_service(session, service_id)
    master = await get_master(session, master_id)
    s_name = service.name if service else ""
    m_name = master.name if master else ""
    date_str = format_date_long(target_date)
    text = (
        f"🕐 <b>Выберите время:</b>\n\n"
        f"Услуга: {s_name}\nМастер: {m_name}\nДата: {date_str}"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=times_kb(slots, master_id, service_id, target_date),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, session) -> None:
    """Выбрано время — показать подтверждение записи."""
    parts = callback.data.split(":")
    master_id = int(parts[1])
    service_id = int(parts[2])
    date_iso = parts[3]
    time_str = parts[4]
    target_date = date.fromisoformat(date_iso)
    # time_str "14:00" -> time
    hour, minute = map(int, time_str.split(":"))
    time_start = time(hour, minute)
    service = await get_service(session, service_id)
    master = await get_master(session, master_id)
    if not service or not master:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    from datetime import timedelta
    end_dt = datetime.combine(target_date, time_start) + timedelta(
        minutes=service.duration_minutes
    )
    time_end = end_dt.time()
    date_display = format_date_long(target_date)
    text = (
        "📋 <b>Подтвердите запись:</b>\n\n"
        f"💈 Услуга: {service.name} ({service.duration_minutes} мин)\n"
        f"👤 Мастер: {master.name}\n"
        f"📅 Дата: {date_display}\n"
        f"🕐 Время: {time_str} — {time_end.strftime('%H:%M')}\n"
        f"💰 Стоимость: {service.price:,.0f} ₽\n\n"
        "Всё верно?"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=confirm_booking_kb(
            master_id, service_id, target_date, time_start
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_book:"))
async def cb_confirm_book(
    callback: CallbackQuery,
    session,
    bot,
    state: FSMContext,
) -> None:
    """Подтвердить запись, создать бронь, уведомить админов."""
    parts = callback.data.split(":")
    master_id = int(parts[1])
    service_id = int(parts[2])
    date_iso = parts[3]
    time_str = parts[4]
    target_date = date.fromisoformat(date_iso)
    hour, minute = map(int, time_str.split(":"))
    time_start = time(hour, minute)
    if not callback.from_user:
        return
    try:
        booking = await create_booking(
            session,
            callback.from_user.id,
            master_id,
            service_id,
            target_date,
            time_start,
        )
    except Exception:
        await callback.answer("Не удалось создать запись", show_alert=True)
        return
    service = await get_service(session, service_id)
    master = await get_master(session, master_id)
    s_name = service.name if service else ""
    m_name = master.name if master else ""
    price = service.price if service else 0
    text = (
        "✅ <b>Вы записаны!</b>\n\n"
        f"💈 {s_name}\n"
        f"👤 {m_name}\n"
        f"📅 {target_date.strftime('%d.%m.%Y')} в {time_str}\n"
        f"💰 {price:,.0f} ₽\n\n"
        "Мы пришлём напоминание за час до визита."
    )
    await edit_safe(callback.message, text, reply_markup=main_menu_kb())
    await state.clear()
    await callback.answer()
    # Уведомление админам
    admin_text = (
        "🆕 <b>Новая запись!</b>\n\n"
        f"💈 {s_name}\n👤 {m_name}\n"
        f"📅 {target_date.strftime('%d.%m.%Y')} в {time_str}\n"
        f"👤 Клиент: {callback.from_user.full_name or '—'} (@{callback.from_user.username or '—'})"
    )
    for admin_id in _config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
            )
        except Exception:
            pass


# --- Мои записи ---


@router.callback_query(F.data == "my_bookings")
async def cb_my_bookings(callback: CallbackQuery, session) -> None:
    """Показать предстоящие записи."""
    if not callback.from_user:
        return
    bookings = await get_user_bookings(session, callback.from_user.id, only_upcoming=True)
    if not bookings:
        text = "📅 У вас нет предстоящих записей."
        await edit_safe(callback.message, text, reply_markup=main_menu_kb())
    else:
        text = "📅 <b>Ваши записи:</b>"
        await edit_safe(
            callback.message,
            text,
            reply_markup=my_bookings_kb(bookings),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("bk:"))
async def cb_bk_detail(callback: CallbackQuery, session) -> None:
    """Детали одной записи."""
    if not callback.from_user:
        return
    _, bid = callback.data.split(":", 1)
    booking_id = int(bid)
    booking = await get_booking(session, booking_id)
    if not booking:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    user = await get_or_create_user(
        session,
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name or "",
    )
    if booking.user_id != user.id:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    status_emoji = {"confirmed": "✅", "cancelled": "❌", "completed": "✔️", "no_show": "⏭"}
    em = status_emoji.get(booking.status, "•")
    text = (
        f"📋 <b>Запись #{booking.id}</b>\n\n"
        f"💈 {booking.service.name} ({booking.service.duration_minutes} мин)\n"
        f"👤 Мастер: {booking.master.name}\n"
        f"📅 {booking.date.strftime('%d.%m.%Y')} в {booking.time_start.strftime('%H:%M')}\n"
        f"💰 {booking.service.price:,.0f} ₽\n"
        f"Статус: {em} {booking.status}"
    )
    await edit_safe(
        callback.message,
        text,
        reply_markup=booking_detail_kb(booking_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_bk:"))
async def cb_cancel_bk(
    callback: CallbackQuery,
    session,
    state: FSMContext,
) -> None:
    """Отменить запись."""
    if not callback.from_user:
        return
    _, bid = callback.data.split(":", 1)
    booking_id = int(bid)
    result = await cancel_booking(
        session, booking_id, callback.from_user.id
    )
    if result is None:
        await callback.answer("Ошибка отмены", show_alert=True)
        return
    await state.clear()
    text = "❌ Запись отменена."
    await edit_safe(callback.message, text, reply_markup=main_menu_kb())
    await callback.answer()
