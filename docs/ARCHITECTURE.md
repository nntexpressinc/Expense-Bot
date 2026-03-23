# 📊 Архитектура Expenses Bot

## 🎯 Обзор системы

Expenses Bot — это асинхронный Telegram-бот для учёта финансов с уникальной функцией контролируемых переводов между пользователями.

## 🏗️ Компоненты системы

### 1. Telegram Bot Layer (aiogram)
- **Handlers**: Обработчики команд и callback
- **Keyboards**: Генераторы клавиатур
- **Middlewares**: Промежуточные обработчики (auth, logging, i18n)
- **States**: FSM состояния для диалогов

### 2. Core Business Logic
- **Services**: Бизнес-логика (TransferService, TransactionService)
- **Repositories**: Абстракция работы с БД
- **Utils**: Вспомогательные функции

### 3. Database Layer
- **Models**: SQLAlchemy ORM модели
- **Migrations**: Alembic миграции
- **Session Management**: Управление сессиями БД

### 4. Background Tasks (Celery)
- **Reports Generation**: Асинхронная генерация отчётов
- **Notifications**: Отправка напоминаний
- **Data Cleanup**: Очистка старых данных

### 5. External Services
- **Exchange Rate API**: Получение курсов валют
- **Monitoring**: Sentry для ошибок, Prometheus для метрик

## 🔄 Потоки данных

### Добавление расхода
```
User → Telegram → Handler → Service → Repository → Database
                                               ↓
                                            Balance Update
                                               ↓
                                            Response → User
```

### Перевод с контролем
```
Sender → Create Transfer → Database (pending)
                              ↓
                        Notification → Recipient
                              ↓
                        Recipient Accept
                              ↓
                        Status: completed
                              ↓
         Recipient spends → Transfer Expense recorded
                              ↓
                        Notification → Sender
```

## 📊 Схема базы данных

### Основные связи
```
User (1) ──→ (*) Transaction
User (1) ──→ (*) Transfer (sender)
User (1) ──→ (*) Transfer (recipient)
Transfer (1) ──→ (*) TransferExpense
Transaction (1) ──→ (1) TransferExpense
Category (1) ──→ (*) Transaction
```

### Ключевые таблицы
- **users**: Пользователи бота
- **transactions**: Все финансовые операции
- **transfers**: Переводы между пользователями
- **transfer_expenses**: Детализация расходов из переводов
- **balances**: Кэш текущих балансов

## 🔐 Безопасность

### Уровни защиты
1. **Аутентификация**: Только через Telegram (OAuth)
2. **Авторизация**: Проверка прав доступа к данным
3. **Шифрование**: AES-256 для sensitive данных
4. **Rate Limiting**: Ограничение запросов
5. **SQL Injection Prevention**: Prepared statements (SQLAlchemy)

### Isolation
- Каждый пользователь видит только свои данные
- Отправитель перевода видит только расходы из своего перевода
- Получатель не видит другие переводы отправителя

## ⚡ Производительность

### Оптимизации
1. **Database Indexes**: На часто используемых полях
2. **Connection Pooling**: Пул соединений к БД
3. **Redis Caching**: Кэширование балансов и сессий
4. **Async Operations**: Асинхронная обработка всех I/O
5. **Pagination**: Ограничение выборки данных

### Масштабирование
- **Horizontal Scaling**: Несколько инстансов бота за load balancer
- **Database Replication**: Master-Slave репликация PostgreSQL
- **Redis Cluster**: Для высокой доступности кэша
- **Celery Workers**: Масштабирование фоновых задач

## 🔄 Жизненный цикл транзакции

### 1. Создание транзакции
```python
transaction = Transaction(
    user_id=user_id,
    type=TransactionType.EXPENSE,
    amount=amount,
    category_id=category_id
)
session.add(transaction)
await session.commit()
```

### 2. Обновление баланса
```python
await recalculate_balance(user_id, currency)
```

### 3. Уведомления (если нужны)
```python
if settings.ENABLE_NOTIFICATIONS:
    await send_notification(user_id, notification_type)
```

### 4. Логирование
```python
logger.info(
    "transaction_created",
    user_id=user_id,
    type=type,
    amount=amount
)
```

## 📈 Мониторинг

### Ключевые метрики
- **Response Time**: p50, p95, p99 времени ответа
- **Error Rate**: % ошибочных запросов
- **Active Users**: DAU, MAU
- **Transaction Volume**: Кол-во транзакций/день
- **Database Performance**: Query time, connection pool usage

### Алерты
- Response time > 1s
- Error rate > 5%
- Database connection pool > 80%
- Disk space < 20%
- Memory usage > 90%

## 🧪 Тестирование

### Unit Tests
```python
@pytest.mark.asyncio
async def test_create_transaction():
    transaction = await create_transaction(
        user_id=123,
        amount=100.0,
        type=TransactionType.INCOME
    )
    assert transaction.amount == 100.0
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_transfer_flow():
    # Create transfer
    transfer = await create_transfer(sender_id, recipient_id, amount)
    assert transfer.status == TransferStatus.PENDING
    
    # Accept transfer
    await accept_transfer(transfer.id, recipient_id)
    assert transfer.status == TransferStatus.COMPLETED
```

## 🚀 Deployment

### Development
```bash
python main.py
```

### Production (Docker)
```bash
docker-compose up -d
```

### Kubernetes (Future)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: expenses-bot
spec:
  replicas: 3
  ...
```

## 📚 Дополнительные ресурсы

- [README.md](README.md) - Полная документация
- [QUICK_START.md](QUICK_START.md) - Быстрый старт
- [database/schema.sql](database/schema.sql) - SQL схема
