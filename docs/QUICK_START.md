# Expenses Bot - Quick Start Guide

## 🚀 Быстрый старт

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/yourusername/expenses-bot.git
cd expenses-bot
```

### 2. Создайте виртуальное окружение
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройте переменные окружения
```bash
# Скопируйте пример конфигурации
copy .env.example .env

# Отредактируйте .env и добавьте ваш токен бота
# TELEGRAM_BOT_TOKEN=your_token_here
```

### 5. Запустите базу данных (Docker)
```bash
docker-compose up -d postgres redis
```

### 6. Примените миграции
```bash
# Создайте базу данных вручную или выполните:
psql -U postgres -c "CREATE DATABASE expenses_bot;"

# Примените SQL-схему
psql -U expenses_user -d expenses_bot -f database/schema.sql
```

### 7. Запустите бота
```bash
python main.py
```

## 📦 Запуск через Docker (рекомендуется)

```bash
# Соберите и запустите все сервисы
docker-compose up -d

# Проверьте логи
docker-compose logs -f bot

# Остановите все сервисы
docker-compose down
```

## 🔧 Разработка

### Структура проекта
```
expenses-bot/
├── bot/               # Логика Telegram-бота
├── core/              # Бизнес-логика
├── database/          # Модели и миграции БД
├── config/            # Конфигурация
├── tasks/             # Celery задачи
└── main.py           # Точка входа
```

### Добавление новых handlers
1. Создайте файл в `bot/handlers/`
2. Импортируйте router в `main.py`
3. Зарегистрируйте: `dp.include_router(your_router)`

### Работа с БД
```python
from database.session import get_session
from database.models import User

async with get_session() as session:
    user = await session.get(User, user_id)
```

## 📝 Полная документация

См. [README.md](README.md) для детальной информации.

## 🐛 Поддержка

Нашли баг? Создайте issue на GitHub!
