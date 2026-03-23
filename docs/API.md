# API Documentation

## Внутренние сервисы (для будущей разработки)

### TransactionService

#### create_transaction()
```python
async def create_transaction(
    user_id: int,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    category_id: Optional[int] = None,
    description: Optional[str] = None,
    transfer_id: Optional[UUID] = None
) -> Transaction
```

Создаёт новую транзакцию.

**Параметры:**
- `user_id`: ID пользователя Telegram
- `type`: Тип транзакции (income/expense/transfer_out/transfer_in)
- `amount`: Сумма транзакции
- `currency`: Валюта (RUB, USD, EUR)
- `category_id`: ID категории (опционально)
- `description`: Описание (опционально)
- `transfer_id`: ID перевода (для transfer_expenses)

**Возвращает:** Объект Transaction

**Исключения:**
- `InsufficientBalanceError`: Недостаточно средств
- `InvalidAmountError`: Некорректная сумма
- `CategoryNotFoundError`: Категория не найдена

---

### TransferService

#### create_transfer()
```python
async def create_transfer(
    sender_id: int,
    recipient_id: int,
    amount: Decimal,
    currency: str,
    description: Optional[str] = None
) -> Transfer
```

Создаёт перевод между пользователями.

**Параметры:**
- `sender_id`: ID отправителя
- `recipient_id`: ID получателя
- `amount`: Сумма перевода
- `currency`: Валюта
- `description`: Комментарий к переводу

**Возвращает:** Объект Transfer со статусом PENDING

**Исключения:**
- `SelfTransferError`: Попытка перевода самому себе
- `UserNotFoundError`: Получатель не найден
- `InsufficientBalanceError`: Недостаточно средств

---

#### accept_transfer()
```python
async def accept_transfer(
    transfer_id: UUID,
    recipient_id: int
) -> Transfer
```

Получатель принимает перевод.

**Параметры:**
- `transfer_id`: ID перевода
- `recipient_id`: ID получателя (для проверки прав)

**Возвращает:** Обновлённый объект Transfer со статусом COMPLETED

---

#### spend_from_transfer()
```python
async def spend_from_transfer(
    transfer_id: UUID,
    user_id: int,
    amount: Decimal,
    category_id: int,
    description: Optional[str] = None
) -> TransferExpense
```

Получатель тратит средства из перевода.

**Параметры:**
- `transfer_id`: ID перевода
- `user_id`: ID получателя
- `amount`: Сумма расхода
- `category_id`: Категория расхода
- `description`: Описание

**Возвращает:** Объект TransferExpense

**Исключения:**
- `InsufficientTransferBalanceError`: Сумма превышает остаток перевода
- `TransferNotFoundError`: Перевод не найден
- `UnauthorizedError`: Пользователь не является получателем

---

### BalanceService

#### get_user_balance()
```python
async def get_user_balance(
    user_id: int,
    currency: str = "RUB"
) -> Dict[str, Decimal]
```

Получает баланс пользователя.

**Параметры:**
- `user_id`: ID пользователя
- `currency`: Валюта (по умолчанию RUB)

**Возвращает:**
```python
{
    "total_balance": Decimal("12450.00"),
    "own_balance": Decimal("9450.00"),
    "received_balance": Decimal("3000.00"),
    "currency": "RUB"
}
```

---

#### recalculate_balance()
```python
async def recalculate_balance(
    user_id: int,
    currency: str = "RUB"
) -> None
```

Пересчитывает и обновляет баланс пользователя.

---

### StatisticsService

#### get_user_stats()
```python
async def get_user_stats(
    user_id: int,
    period: str = "month",  # day, week, month, year
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict
```

Получает статистику пользователя за период.

**Возвращает:**
```python
{
    "period": "Февраль 2026",
    "total_income": Decimal("50000.00"),
    "total_expense": Decimal("37550.00"),
    "difference": Decimal("12450.00"),
    "top_categories": [
        {
            "name": "Еда",
            "icon": "🍔",
            "amount": Decimal("15200.00"),
            "percent": 40.5,
            "transaction_count": 28
        }
    ],
    "transfers_sent": {
        "amount": Decimal("8000.00"),
        "count": 3
    },
    "transfers_received": {
        "amount": Decimal("5000.00"),
        "count": 2
    }
}
```

---

### ReportService

#### generate_report()
```python
async def generate_report(
    user_id: int,
    report_type: ReportType,
    format: ReportFormat,
    start_date: date,
    end_date: date
) -> str
```

Генерирует отчёт и возвращает путь к файлу.

**Параметры:**
- `user_id`: ID пользователя
- `report_type`: Тип отчёта (daily/weekly/monthly/custom)
- `format`: Формат (pdf/excel)
- `start_date`: Начало периода
- `end_date`: Конец периода

**Возвращает:** Путь к сгенерированному файлу

---

## Webhook API (для будущей интеграции)

### POST /webhook/telegram
Webhook для получения обновлений от Telegram.

### GET /health
Healthcheck endpoint для мониторинга.

**Ответ:**
```json
{
    "status": "ok",
    "version": "1.0.0",
    "database": "connected",
    "redis": "connected"
}
```

### GET /metrics
Prometheus метрики.

---

## Database Functions

### recalculate_balance()
```sql
SELECT recalculate_balance(user_id BIGINT, currency VARCHAR(3));
```

Пересчитывает баланс пользователя на уровне БД.

---

## Redis Keys

### User State
```
user_state:{user_id}
```
TTL: 1 hour
Содержит FSM состояние пользователя.

### Rate Limit
```
rate_limit:{user_id}
```
TTL: 60 seconds
Счётчик запросов для rate limiting.

### Balance Cache
```
cache_balance:{user_id}
```
TTL: 5 minutes
Кэшированный баланс пользователя.

---

## Events / Notifications

### transfer.received
Отправляется когда пользователь получает перевод.

### transfer.spent
Отправляется отправителю когда получатель тратит средства.

### daily.reminder
Ежедневное напоминание о внесении расходов.

### budget.warning
Предупреждение о превышении бюджета категории.

---

## Error Codes

| Code | Description |
|------|-------------|
| 1001 | Insufficient balance |
| 1002 | User not found |
| 1003 | Invalid amount |
| 1004 | Self transfer error |
| 1005 | Transfer not found |
| 1006 | Category not found |
| 1007 | Unauthorized access |
| 2001 | Database error |
| 2002 | Redis connection error |
| 3001 | Rate limit exceeded |
| 3002 | Invalid input |
