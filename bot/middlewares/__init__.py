# bot/middlewares/__init__.py
from bot.middlewares.db import DbSessionMiddleware

__all__ = ["DbSessionMiddleware"]
