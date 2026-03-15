# bot/services/scheduler.py — напоминания о записях (APScheduler)
from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from bot.services.db import (
    get_upcoming_bookings_for_reminder,
    mark_reminder_sent,
)

logger = logging.getLogger(__name__)


def setup_scheduler(
    bot: Any,
    session_pool: async_sessionmaker[AsyncSession],
    config: Any,
) -> AsyncIOScheduler:
    """
    Настраивает APScheduler: каждые 5 минут проверяет записи,
    до начала которых <= REMINDER_MINUTES минут, отправляет напоминание,
    помечает reminder_sent=True.
    """
    scheduler = AsyncIOScheduler()
    reminder_minutes = getattr(config, "REMINDER_MINUTES", 60)

    async def send_reminders() -> None:
        async with session_pool() as session:
            try:
                bookings = await get_upcoming_bookings_for_reminder(
                    session, reminder_minutes
                )
                for booking in bookings:
                    try:
                        text = (
                            "⏰ <b>Напоминание о записи!</b>\n\n"
                            f"📋 Услуга: {booking.service.name}\n"
                            f"👤 Мастер: {booking.master.name}\n"
                            f"📅 {booking.date.strftime('%d.%m.%Y')} "
                            f"в {booking.time_start.strftime('%H:%M')}\n\n"
                            "Ждём вас!"
                        )
                        await bot.send_message(
                            chat_id=booking.user.telegram_id,
                            text=text,
                            parse_mode="HTML",
                        )
                        await mark_reminder_sent(session, booking.id)
                    except Exception as e:
                        logger.warning(
                            "Не удалось отправить напоминание booking_id=%s: %s",
                            booking.id,
                            e,
                        )
            except Exception as e:
                logger.exception("Ошибка в задаче напоминаний: %s", e)

    scheduler.add_job(
        send_reminders,
        "interval",
        minutes=5,
        id="reminders",
    )
    scheduler.start()
    logger.info("Планировщик напоминаний запущен (интервал 5 мин).")
    return scheduler
