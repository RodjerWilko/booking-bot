#!/bin/bash
# Деплой BookingBot на VPS. Запускать с машины с sshpass (Linux/WSL).
# Использование: ./deploy_vps.sh

set -e
SSH="sshpass -p 'tef-7#2v#auLP2' ssh -o StrictHostKeyChecking=no root@147.45.243.199"

echo "=== 1. Создание БД bookingbot ==="
$SSH "docker exec shop-bot-db-1 psql -U shopbot -c 'CREATE DATABASE bookingbot;'" 2>/dev/null || true

echo "=== 2. Клонирование и настройка ==="
$SSH << 'ENDSSH'
cd /opt/bots
rm -rf booking-bot
git clone https://github.com/RodjerWilko/booking-bot.git
cd booking-bot

cat > .env << 'ENVEOF'
BOT_TOKEN=8794284912:AAGGKVS8JHa64bUgtY0KXtK6ntSZPQ9cQYA
ADMIN_IDS=52178124
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot_secret@db:5432/bookingbot
REMINDER_MINUTES=60
BUSINESS_NAME=Студия красоты
WORK_START_HOUR=9
WORK_END_HOUR=21
ENVEOF

cat > update.sh << 'UPDEOF'
#!/bin/bash
cd /opt/bots/booking-bot
git pull origin main
docker compose up -d --build
docker compose logs bot --tail 20
echo "✅ Обновление завершено"
UPDEOF
chmod +x update.sh
ENDSSH

echo "=== 3. Запуск контейнера ==="
$SSH << 'ENDSSH'
cd /opt/bots/booking-bot
docker compose up -d --build
sleep 15
docker compose ps
docker compose logs bot --tail 30
ENDSSH

echo "=== 4. Проверка ShopBot ==="
$SSH "cd /opt/bots/shop-bot && docker compose ps" 2>/dev/null || true

echo "=== Готово ==="
