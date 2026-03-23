# 📚 Навигация по проекту Expenses Bot

Добро пожаловать в документацию Telegram-бота для учёта финансов!

---

## 🚀 Быстрый старт

Хотите сразу запустить бот?  
→ **[QUICK_START.md](QUICK_START.md)** - пошаговая инструкция за 5 минут

---

## 📖 Документация по разделам

### Для первого знакомства
1. **[README.md](README.md)** 📄  
   Начните отсюда! Полное описание проекта, архитектура, основные команды, сценарии использования.

2. **[SUMMARY.md](SUMMARY.md)** 🎉  
   Краткая сводка: что создано, метрики проекта, готовый функционал, планы на будущее.

### Для разработчиков

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** 🏗️  
   Детальное описание архитектуры: компоненты, потоки данных, безопасность, производительность.

4. **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** 📁  
   Структура файлов и папок с описанием каждого компонента. Статус реализации.

5. **[API.md](API.md)** 🔌  
   Документация всех сервисов, функций, endpoints. Параметры, возвращаемые значения, исключения.

6. **[DIAGRAMS.md](DIAGRAMS.md)** 📊  
   Визуальные схемы: архитектура компонентов, потоки данных, ER-диаграммы, FSM состояния.

### Для понимания функционала

7. **[EXAMPLES.md](EXAMPLES.md)** 🎓  
   8 детальных примеров использования с диалогами, кодом и SQL-запросами. Edge cases.

---

## 🗂️ Структура проекта

```
expenses-bot/
├── 📚 Документация (8 файлов)
│   ├── README.md              # Главный документ
│   ├── QUICK_START.md         # Быстрый старт
│   ├── SUMMARY.md             # Итоговая сводка
│   ├── ARCHITECTURE.md        # Архитектура
│   ├── PROJECT_STRUCTURE.md   # Структура файлов
│   ├── API.md                 # API документация
│   ├── EXAMPLES.md            # Примеры
│   ├── DIAGRAMS.md            # Диаграммы
│   └── INDEX.md               # Этот файл
│
├── 💻 Исходный код
│   ├── main.py                # Точка входа
│   ├── config/                # Настройки
│   ├── database/              # БД (models, schema.sql)
│   ├── bot/                   # Handlers, keyboards, states
│   └── core/                  # Services (TODO)
│
└── 🐳 Infrastructure
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    └── .env.example
```

---

## 🎯 Навигация по задачам

### Хочу запустить проект локально
→ [QUICK_START.md](QUICK_START.md) → Раздел "Быстрый старт"

### Хочу понять, как работает бот
→ [EXAMPLES.md](EXAMPLES.md) → Примеры 1-8

### Хочу изучить архитектуру системы
→ [ARCHITECTURE.md](ARCHITECTURE.md) → Полное описание

### Хочу увидеть схемы и диаграммы
→ [DIAGRAMS.md](DIAGRAMS.md) → Визуальные схемы

### Хочу начать разработку
→ [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) → Статус реализации → TODO список

### Хочу понять API сервисов
→ [API.md](API.md) → Документация сервисов

### Хочу узнать, что уже готово
→ [SUMMARY.md](SUMMARY.md) → Раздел "Что было создано"

---

## 🔍 Поиск по темам

### База данных
- Схема: [database/schema.sql](database/schema.sql)
- ORM модели: [database/models.py](database/models.py)
- Описание таблиц: [README.md](README.md#структура-базы-данных)
- ER-диаграмма: [DIAGRAMS.md](DIAGRAMS.md#er-diagram)

### Handlers бота
- start, help: [bot/handlers/start.py](bot/handlers/start.py)
- Доходы: [bot/handlers/income.py](bot/handlers/income.py)
- Расходы: [bot/handlers/expense.py](bot/handlers/expense.py)
- Переводы: [bot/handlers/transfer.py](bot/handlers/transfer.py)
- Статистика: [bot/handlers/stats.py](bot/handlers/stats.py)

### Конфигурация
- Настройки: [config/settings.py](config/settings.py)
- Константы: [config/constants.py](config/constants.py)
- Переменные окружения: [.env.example](.env.example)

### Deployment
- Docker: [Dockerfile](Dockerfile)
- Docker Compose: [docker-compose.yml](docker-compose.yml)
- Инструкции: [QUICK_START.md](QUICK_START.md#запуск-через-docker)

---

## 💡 Полезные ссылки

### Внешняя документация
- [Aiogram 3 Docs](https://docs.aiogram.dev/en/latest/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Инструменты разработки
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis 7
- VS Code (рекомендуется)

---

## 🎬 Сценарии использования

### Я — новый разработчик в проекте
1. Прочитайте [README.md](README.md) для общего понимания
2. Изучите [ARCHITECTURE.md](ARCHITECTURE.md) для понимания архитектуры
3. Следуйте [QUICK_START.md](QUICK_START.md) для локального запуска
4. Посмотрите [EXAMPLES.md](EXAMPLES.md) для понимания flow
5. Изучите [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) для понимания кодовой базы
6. Выберите задачу из TODO списка и начинайте!

### Я — тимлид / архитектор
1. [ARCHITECTURE.md](ARCHITECTURE.md) - оцените архитектурные решения
2. [DIAGRAMS.md](DIAGRAMS.md) - визуализация компонентов
3. [API.md](API.md) - проверьте контракты сервисов
4. [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - статус реализации
5. [SUMMARY.md](SUMMARY.md) - метрики и планы

### Я — продакт-менеджер
1. [README.md](README.md) - функционал и возможности
2. [EXAMPLES.md](EXAMPLES.md) - пользовательские сценарии
3. [SUMMARY.md](SUMMARY.md) - что готово, что в планах
4. [README.md - Roadmap](README.md#roadmap) - план развития

### Я — тестировщик
1. [EXAMPLES.md](EXAMPLES.md) - тестовые сценарии
2. [README.md - Edge Cases](README.md#edge-cases) - граничные случаи
3. [API.md](API.md) - API контракты для тестирования
4. [QUICK_START.md](QUICK_START.md) - локальный запуск для тестов

---

## ❓ FAQ

### Где найти команды бота?
[README.md](README.md#основные-команды-telegram-бота)

### Как работают контролируемые переводы?
[README.md](README.md#сценарий-2-перевод-с-контролем) или [EXAMPLES.md](EXAMPLES.md#пример-2-перевод-с-контролем)

### Какие технологии использованы?
[README.md](README.md#tech-stack) или [ARCHITECTURE.md](ARCHITECTURE.md#tech-stack)

### Как запустить в production?
[QUICK_START.md](QUICK_START.md#production-docker)

### Где схема базы данных?
[database/schema.sql](database/schema.sql) или [README.md](README.md#структура-базы-данных)

### Что уже реализовано?
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md#статус-реализации) или [SUMMARY.md](SUMMARY.md#что-было-создано)

### Что нужно доработать?
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md#в-разработке-todo) или [SUMMARY.md](SUMMARY.md#что-осталось-доработать)

---

## 📊 Статистика проекта

- **Документация:** 8 файлов, ~3000 строк
- **Исходный код:** ~3000 строк Python + 500 строк SQL
- **Database:** 8 таблиц, 8 моделей
- **Handlers:** 5 полных flow
- **Статус:** MVP готов к запуску и тестированию

---

## 🤝 Контрибьютинг

Планируете внести вклад? Отлично!

1. Изучите [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - структура проекта
2. Выберите задачу из TODO списка
3. Следуйте существующему стилю кода
4. Пишите тесты для новых функций
5. Обновляйте документацию при необходимости

---

## 📞 Поддержка

Возникли вопросы?

1. Проверьте [FAQ](#faq)
2. Изучите соответствующий раздел документации
3. Создайте issue на GitHub
4. Свяжитесь с командой

---

## 🎉 Начните сейчас!

**Выберите свой путь:**

- 🚀 [Запустить локально](QUICK_START.md)
- 📖 [Изучить архитектуру](ARCHITECTURE.md)
- 💻 [Начать разработку](PROJECT_STRUCTURE.md)
- 🎓 [Посмотреть примеры](EXAMPLES.md)
- 📊 [Увидеть схемы](DIAGRAMS.md)

---

**Expenses Bot** — учёт расходов с контролем переводов 💰  
Версия: v0.1.0-alpha (MVP)  
Дата создания: 11 февраля 2026

**Удачи в работе с проектом!** 🚀
