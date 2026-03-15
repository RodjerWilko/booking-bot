# bot/config.py — конфигурация из .env (как в ShopBot)
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Конфигурация бота. Загрузка из переменных окружения."""

    BOT_TOKEN: str
    ADMIN_IDS: list[int]
    DATABASE_URL: str
    REMINDER_MINUTES: int = 60
    BUSINESS_NAME: str = "Студия красоты"
    WORK_START_HOUR: int = 9
    WORK_END_HOUR: int = 21

    @classmethod
    def from_env(cls) -> Config:
        token = os.getenv("BOT_TOKEN", "")
        admin_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = [int(x.strip()) for x in admin_raw.split(",") if x.strip()]
        db_url = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./booking.db",
        )
        reminder = int(os.getenv("REMINDER_MINUTES", "60"))
        business = os.getenv("BUSINESS_NAME", "Студия красоты")
        work_start = int(os.getenv("WORK_START_HOUR", "9"))
        work_end = int(os.getenv("WORK_END_HOUR", "21"))
        return cls(
            BOT_TOKEN=token,
            ADMIN_IDS=admin_ids,
            DATABASE_URL=db_url,
            REMINDER_MINUTES=reminder,
            BUSINESS_NAME=business,
            WORK_START_HOUR=work_start,
            WORK_END_HOUR=work_end,
        )
