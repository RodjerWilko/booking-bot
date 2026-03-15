# BookingBot — образ для запуска в Docker (общая сеть с ShopBot)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Запуск из корня проекта, чтобы bot был пакетом
ENV PYTHONPATH=/app
CMD ["python", "-m", "bot.main"]
