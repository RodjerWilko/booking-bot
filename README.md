# 📅 BookingBot — Telegram-бот онлайн-записи

> Бот для онлайн-записи клиентов в барбершопы, салоны красоты, клиники и студии. Выбор услуги → мастера → даты → времени за 4 нажатия. Автоматические напоминания. Single-message UI.

## 🔗 [Живой бот: @RWdev_bookingBot](https://t.me/RWdev_bookingBot)

## Возможности

### Для клиентов
- 💈 Выбор услуги, мастера, даты и времени
- 📅 Просмотр и отмена своих записей
- ⏰ Автоматическое напоминание за час до визита
- 💬 Навигация в одном сообщении — без спама

### Для администратора
- 📊 Статистика (клиенты, записи, выручка)
- 📅 Расписание записей на сегодня
- 👥 Управление мастерами и услугами
- 🔔 Уведомления о новых записях

## Стек

Python 3.11 | aiogram 3.x | SQLAlchemy 2.0 | PostgreSQL | APScheduler | Docker

## Архитектура

- **Single-message UI** — вся навигация через редактирование одного сообщения
- Слоёная структура: config → models → services → keyboards → handlers
- Планировщик напоминаний (APScheduler, проверка каждые 5 мин)
- Генерация свободных слотов с учётом расписания мастера и существующих броней

## Быстрый старт

```bash
git clone https://github.com/RodjerWilko/booking-bot.git
cd booking-bot
cp .env.example .env
# Заполните BOT_TOKEN и ADMIN_IDS в .env
pip install -r requirements.txt
python -m bot.main
```

Для запуска в Docker (общий PostgreSQL с другим проектом):

```bash
# На сервере с уже запущенным PostgreSQL (например ShopBot):
# docker exec shop-bot-db-1 psql -U shopbot -c "CREATE DATABASE bookingbot;"
docker compose up -d --build
```

## Структура проекта

```
booking-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── utils.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── user.py      # /start, запись, мои записи
│   │   └── admin.py     # /admin, статистика, мастера, услуги
│   ├── models/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── database.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── db.py        # CRUD
│   │   └── scheduler.py # Напоминания
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── kb.py
│   └── middlewares/
│       ├── __init__.py
│       └── db.py
├── reports/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Переменные окружения

| Переменная        | Описание |
|-------------------|----------|
| `BOT_TOKEN`       | Токен бота от @BotFather |
| `ADMIN_IDS`       | ID администраторов через запятую (Telegram user id) |
| `DATABASE_URL`    | URL БД, например `postgresql+asyncpg://user:pass@host:5432/bookingbot` или `sqlite+aiosqlite:///./booking.db` |
| `REMINDER_MINUTES`| За сколько минут до записи отправлять напоминание (по умолчанию 60) |
| `BUSINESS_NAME`   | Название бизнеса (по умолчанию «Студия красоты») |
| `WORK_START_HOUR` | Начало рабочего дня, час (по умолчанию 9) |
| `WORK_END_HOUR`   | Конец рабочего дня, час (по умолчанию 21) |

## Лицензия

MIT
