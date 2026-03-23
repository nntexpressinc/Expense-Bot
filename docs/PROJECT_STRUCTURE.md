# 📁 Структура проекта Expenses Bot

Полная файловая структура Telegram-бота для учёта расходов с функцией контролируемых переводов.

```
expenses-bot/
│
├── 📄 README.md                    # Основная документация проекта
├── 📄 QUICK_START.md               # Руководство по быстрому старту
├── 📄 ARCHITECTURE.md              # Описание архитектуры системы
├── 📄 API.md                       # API документация (сервисы, функции)
├── 📄 EXAMPLES.md                  # Примеры использования бота
├── 📄 DIAGRAMS.md                  # Визуальные схемы и диаграммы
├── 📄 PROJECT_STRUCTURE.md         # Этот файл - структура проекта
│
├── 📄 main.py                      # Точка входа приложения
├── 📄 requirements.txt             # Python зависимости
├── 📄 .env.example                 # Пример конфигурации
├── 📄 .gitignore                   # Игнорируемые файлы для Git
├── 📄 Dockerfile                   # Docker образ для бота
├── 📄 docker-compose.yml           # Docker Compose конфигурация
│
├── 📁 config/                      # Конфигурация приложения
│   ├── __init__.py
│   ├── settings.py                # Настройки (Pydantic Settings)
│   └── constants.py               # Константы приложения
│
├── 📁 database/                    # Слой работы с базой данных
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy ORM модели
│   ├── session.py                 # Управление сессиями БД
│   ├── schema.sql                 # SQL схема базы данных
│   └── migrations/                # Alembic миграции (создаётся позже)
│       └── versions/
│
├── 📁 bot/                         # Логика Telegram-бота
│   ├── __init__.py
│   ├── states.py                  # FSM состояния для диалогов
│   │
│   ├── 📁 handlers/                # Обработчики команд
│   │   ├── __init__.py
│   │   ├── start.py               # /start, /help, /cancel
│   │   ├── income.py              # Добавление доходов
│   │   ├── expense.py             # Добавление расходов
│   │   ├── transfer.py            # Переводы между пользователями
│   │   ├── stats.py               # Статистика и баланс
│   │   ├── reports.py             # Генерация отчётов (TODO)
│   │   └── settings.py            # Настройки пользователя (TODO)
│   │
│   ├── 📁 keyboards/               # Клавиатуры (Reply/Inline)
│   │   └── __init__.py            # Функции генерации клавиатур
│   │
│   ├── 📁 middlewares/             # Промежуточные обработчики (TODO)
│   │   ├── __init__.py
│   │   ├── auth.py                # Проверка авторизации
│   │   ├── logging.py             # Логирование запросов
│   │   └── rate_limit.py          # Ограничение запросов
│   │
│   └── 📁 filters/                 # Кастомные фильтры (TODO)
│       ├── __init__.py
│       └── admin.py               # Фильтр для админов
│
├── 📁 core/                        # Бизнес-логика (TODO)
│   ├── __init__.py
│   │
│   ├── 📁 services/                # Сервисы бизнес-логики
│   │   ├── __init__.py
│   │   ├── transaction.py         # Работа с транзакциями
│   │   ├── transfer.py            # Логика переводов
│   │   ├── balance.py             # Управление балансами
│   │   ├── statistics.py          # Статистика пользователей
│   │   ├── report.py              # Генерация отчётов
│   │   └── notification.py        # Отправка уведомлений
│   │
│   ├── 📁 repositories/            # Репозитории для работы с БД
│   │   ├── __init__.py
│   │   ├── user.py                # User CRUD
│   │   ├── transaction.py         # Transaction CRUD
│   │   ├── transfer.py            # Transfer CRUD
│   │   ├── category.py            # Category CRUD
│   │   └── balance.py             # Balance CRUD
│   │
│   └── 📁 utils/                   # Вспомогательные функции
│       ├── __init__.py
│       ├── currency.py            # Конвертация валют
│       ├── date_helpers.py        # Работа с датами
│       ├── validators.py          # Валидация данных
│       └── formatters.py          # Форматирование вывода
│
├── 📁 tasks/                       # Фоновые задачи Celery (TODO)
│   ├── __init__.py
│   ├── celery_app.py              # Конфигурация Celery
│   ├── reports.py                 # Задачи генерации отчётов
│   ├── notifications.py           # Задачи отправки уведомлений
│   └── cleanup.py                 # Очистка старых данных
│
├── 📁 tests/                       # Тесты (TODO)
│   ├── __init__.py
│   ├── conftest.py                # Pytest конфигурация
│   │
│   ├── 📁 unit/                    # Unit тесты
│   │   ├── test_services.py
│   │   ├── test_repositories.py
│   │   └── test_utils.py
│   │
│   ├── 📁 integration/             # Интеграционные тесты
│   │   ├── test_handlers.py
│   │   ├── test_transfers.py
│   │   └── test_database.py
│   │
│   └── 📁 e2e/                     # End-to-end тесты
│       └── test_bot_flow.py
│
├── 📁 logs/                        # Логи приложения (создаётся автоматически)
│   └── .gitkeep
│
├── 📁 reports/                     # Сгенерированные отчёты (создаётся автоматически)
│   └── .gitkeep
│
└── 📁 docs/                        # Дополнительная документация (TODO)
    ├── deployment.md              # Инструкции по развёртыванию
    ├── contributing.md            # Руководство для контрибьюторов
    └── changelog.md               # История изменений
```

---

## 📊 Статус реализации

### ✅ Завершено (MVP)

#### Документация
- [x] README.md - основная документация
- [x] QUICK_START.md - руководство по запуску
- [x] ARCHITECTURE.md - описание архитектуры
- [x] API.md - документация API и сервисов
- [x] EXAMPLES.md - примеры использования
- [x] DIAGRAMS.md - визуальные схемы
- [x] PROJECT_STRUCTURE.md - структура проекта

#### База данных
- [x] SQLAlchemy модели (User, Transaction, Transfer, etc.)
- [x] SQL схема базы данных
- [x] Relationships и constraints
- [x] Indexes для оптимизации

#### Конфигурация
- [x] Pydantic Settings
- [x] Константы приложения
- [x] .env.example
- [x] Docker конфигурация

#### Bot Handlers
- [x] start.py - стартовые команды
- [x] income.py - добавление доходов
- [x] expense.py - добавление расходов
- [x] transfer.py - переводы (базовая логика)
- [x] stats.py - статистика и баланс

#### UI/UX
- [x] Клавиатуры (main menu, categories, confirmation)
- [x] FSM состояния для всех основных flow
- [x] Текстовые сообщения на русском

#### Infrastructure
- [x] main.py - точка входа
- [x] requirements.txt
- [x] Dockerfile
- [x] docker-compose.yml

---

### 🚧 В разработке (TODO)

#### Core Services
- [ ] TransactionService - полная бизнес-логика транзакций
- [ ] TransferService - полная логика переводов
- [ ] BalanceService - управление балансами
- [ ] StatisticsService - расчёт статистики
- [ ] ReportService - генерация отчётов

#### Repositories
- [ ] Реализация всех CRUD операций
- [ ] Оптимизация запросов
- [ ] Pagination для больших выборок

#### Bot Handlers
- [ ] reports.py - генерация и скачивание отчётов
- [ ] settings.py - полные настройки пользователя
- [ ] Обработка ошибок и edge cases
- [ ] Internationalization (i18n)

#### Middlewares
- [ ] auth.py - проверка авторизации
- [ ] logging.py - структурированное логирование
- [ ] rate_limit.py - защита от спама

#### Background Tasks
- [ ] Celery конфигурация
- [ ] Генерация отчётов в фоне
- [ ] Отправка уведомлений
- [ ] Автоматическая очистка данных

#### Тестирование
- [ ] Unit тесты для сервисов
- [ ] Integration тесты для handlers
- [ ] E2E тесты для критических flow
- [ ] Coverage > 80%

#### Monitoring & Logging
- [ ] Sentry интеграция
- [ ] Prometheus метрики
- [ ] Grafana dashboards
- [ ] Structured logging (structlog)

#### Дополнительные функции
- [ ] Мультивалютность
- [ ] Бюджетирование
- [ ] Recurring транзакции
- [ ] Общие бюджеты (семья/команда)
- [ ] AI-рекомендации
- [ ] Голосовой ввод

---

## 📝 Ключевые файлы

### main.py
Точка входа приложения. Инициализирует БД, создаёт bot и dispatcher, регистрирует handlers.

### database/models.py
Все ORM модели SQLAlchemy с relationships и constraints.

### database/schema.sql
Полная SQL схема с таблицами, индексами, функциями и triggers.

### bot/handlers/
Обработчики Telegram команд и callback-запросов. Каждый файл отвечает за свою область (доходы, расходы, переводы).

### bot/keyboards/
Генераторы клавиатур (Reply и Inline) для удобного взаимодействия с ботом.

### bot/states.py
FSM (Finite State Machine) состояния для управления диалогами с пользователем.

### config/settings.py
Конфигурация приложения через Pydantic Settings с загрузкой из .env.

### config/constants.py
Константы: типы транзакций, статусы, текстовые сообщения, лимиты.

---

## 🔧 Зависимости

### Основные
- **aiogram 3.4.1** - асинхронный фреймворк для Telegram Bot API
- **SQLAlchemy 2.0** - ORM для работы с PostgreSQL
- **asyncpg** - async драйвер PostgreSQL
- **pydantic** - валидация данных и настроек
- **redis** - кэширование и сессии

### Фоновые задачи
- **celery** - распределённые задачи
- **flower** - мониторинг Celery

### Отчёты
- **openpyxl** - генерация Excel
- **reportlab** - генерация PDF
- **pandas** - обработка данных

### Мониторинг
- **sentry-sdk** - отслеживание ошибок
- **prometheus-client** - метрики

---

## 🚀 Следующие шаги

1. **Реализовать core services** - бизнес-логику в отдельных классах
2. **Интегрировать services с handlers** - заменить TODO на реальные вызовы
3. **Добавить тесты** - покрытие критических функций
4. **Настроить Celery** - фоновые задачи для отчётов и уведомлений
5. **Реализовать middlewares** - логирование, rate limiting, auth
6. **Добавить мониторинг** - Sentry + Prometheus + Grafana
7. **Развернуть production** - Docker Compose или Kubernetes

---

## 📞 Контакты

Для вопросов по архитектуре и структуре проекта обращайтесь к документации:
- [README.md](README.md) - общий обзор
- [ARCHITECTURE.md](ARCHITECTURE.md) - детали архитектуры
- [QUICK_START.md](QUICK_START.md) - быстрый старт разработки

---

**Проект находится в активной разработке!** 🚀

Текущая версия: **v0.1.0-alpha** (MVP)
Целевая версия: **v1.0.0** (полный функционал)
