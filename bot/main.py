# bot/main.py — точка входа, пул БД, планировщик, роутеры (хендлеры — в итерации 2)
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.handlers import admin, user
from bot.middlewares.db import DbSessionMiddleware
from bot.models.database import create_session_pool, create_tables
from bot.services.db import seed_demo_data
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = Config.from_env()
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не задан")
        return

    session_pool = create_session_pool(config.DATABASE_URL)
    await create_tables(database_url=config.DATABASE_URL)
    async with session_pool() as session:
        await seed_demo_data(session)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DbSessionMiddleware(session_pool))
    dp.callback_query.middleware(DbSessionMiddleware(session_pool))

    dp.include_router(user.router, prefix="/")
    dp.include_router(admin.router, prefix="/admin")

    scheduler = setup_scheduler(bot, session_pool, config)

    try:
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
