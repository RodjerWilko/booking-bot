# bot/utils.py — edit_safe, delete_safe для отказоустойчивой работы с сообщениями
from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


async def edit_safe(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    **kwargs: Any,
) -> bool:
    """
    edit_text с обработкой TelegramBadRequest (например, текст не изменился).
    Возвращает True при успехе, False при ошибке.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
        return True
    except TelegramBadRequest as e:
        logger.debug("edit_safe: %s", e)
        return False


async def delete_safe(bot: Bot, chat_id: int, message_id: int) -> bool:
    """
    delete_message с try/except. Не падает, если сообщение уже удалено.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.debug("delete_safe: %s", e)
        return False
