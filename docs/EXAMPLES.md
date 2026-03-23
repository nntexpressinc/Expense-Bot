# 🎓 Примеры использования Expenses Bot

## Пример 1: Базовый учёт расходов

### Сценарий: Запись похода в магазин

```
Пользователь: /start
Бот: Приветствие + главное меню

Пользователь: ➖ Расход
Бот: Введите сумму расхода

Пользователь: 1250
Бот: Выберите категорию [кнопки категорий]

Пользователь: 🍔 Еда и продукты
Бот: Добавьте описание

Пользователь: Продукты в Пятёрочке
Бот: ✅ Расход 1250 RUB добавлен. Баланс: 8750 RUB
```

### Программная реализация

```python
from bot.handlers.expense import start_add_expense
from database.models import Transaction, TransactionType

# Создание расхода
transaction = Transaction(
    user_id=123456789,
    type=TransactionType.EXPENSE,
    amount=1250.00,
    currency="RUB",
    category_id=8,  # Еда
    description="Продукты в Пятёрочке"
)

await session.add(transaction)
await session.commit()

# Обновление баланса
await recalculate_balance(user_id=123456789, currency="RUB")
```

---

## Пример 2: Перевод с контролем расходов

### Сценарий: Родитель даёт деньги студенту

**Отправитель (Мама):**
```
Мама: /transfer
Бот: Введите @username получателя

Мама: @son
Бот: Введите сумму перевода

Мама: 10000
Бот: Добавьте комментарий

Мама: На месяц (еда + учебники)
Бот: Подтверждение перевода [кнопки]

Мама: ✅ Подтвердить
Бот: ✅ Перевод 10000 RUB отправлен @son
```

**Получатель (Сын):**
```
Сын получает: 💰 @mama отправила 10000 RUB (На месяц)
                [Принять] [Отклонить]

Сын: [Принять]
Бот: ✅ 10000 RUB получены
```

**Сын тратит деньги:**
```
Сын: 💸 Потратить перевод
Бот: Доступно: 10000 RUB от @mama

Сын: [выбирает перевод]
Бот: Введите сумму расхода

Сын: 3500
Бот: Выберите категорию

Сын: 🍔 Еда
Бот: Описание

Сын: Продукты на неделю
Бот: ✅ Расход 3500 RUB учтён
     Остаток перевода: 6500 RUB
```

**Мама получает уведомление:**
```
📊 @son потратил 3500 RUB из вашего перевода
   Категория: 🍔 Еда
   Описание: Продукты на неделю
   Остаток: 6500 RUB
```

### Программная реализация

```python
# 1. Создание перевода
transfer = Transfer(
    sender_id=111111111,  # Мама
    recipient_id=222222222,  # Сын
    amount=10000.00,
    currency="RUB",
    description="На месяц (еда + учебники)",
    status=TransferStatus.PENDING,
    remaining_amount=10000.00
)
await session.add(transfer)
await session.commit()

# 2. Принятие перевода
transfer.status = TransferStatus.COMPLETED
transfer.completed_at = datetime.utcnow()
await session.commit()

# 3. Расход из перевода
expense_transaction = Transaction(
    user_id=222222222,  # Сын
    type=TransactionType.EXPENSE,
    amount=3500.00,
    currency="RUB",
    category_id=8,
    description="Продукты на неделю",
    transfer_id=transfer.id
)

transfer_expense = TransferExpense(
    transfer_id=transfer.id,
    transaction_id=expense_transaction.id,
    amount=3500.00,
    category_id=8,
    description="Продукты на неделю"
)

# Обновляем остаток перевода
transfer.remaining_amount -= 3500.00

await session.add(expense_transaction)
await session.add(transfer_expense)
await session.commit()

# 4. Уведомление отправителю
await send_notification(
    user_id=111111111,
    type="transfer_spent",
    data={
        "recipient": "@son",
        "amount": 3500.00,
        "category": "🍔 Еда",
        "description": "Продукты на неделю",
        "remaining": 6500.00
    }
)
```

---

## Пример 3: Просмотр статистики

### Сценарий: Анализ расходов за месяц

```
Пользователь: /stats
Бот: 
📊 Статистика

📅 Период: Февраль 2026

📈 Доходы: +50,000 RUB
📉 Расходы: -37,550 RUB
📊 Разница: +12,450 RUB

🔝 Топ категорий расходов:
1. 🍔 Еда - 15,200 RUB (40.5%)
2. 🏠 Жильё - 12,000 RUB (32.0%)
3. 🚕 Транспорт - 6,500 RUB (17.3%)

📤 Отправлено переводов: 8,000 RUB (3 чел.)
📥 Получено переводов: 5,000 RUB (2 чел.)
```

### SQL запрос для статистики

```sql
-- Топ категорий расходов за период
SELECT 
    c.name,
    c.icon,
    SUM(t.amount) as total_amount,
    COUNT(t.id) as transaction_count,
    ROUND(SUM(t.amount) / total_expenses.sum * 100, 2) as percentage
FROM transactions t
JOIN categories c ON t.category_id = c.id
CROSS JOIN (
    SELECT SUM(amount) as sum
    FROM transactions
    WHERE user_id = :user_id
      AND type = 'expense'
      AND DATE_TRUNC('month', transaction_date) = :month
) total_expenses
WHERE t.user_id = :user_id
  AND t.type = 'expense'
  AND DATE_TRUNC('month', t.transaction_date) = :month
GROUP BY c.id, c.name, c.icon, total_expenses.sum
ORDER BY total_amount DESC
LIMIT 5;
```

---

## Пример 4: Генерация отчёта

### Сценарий: Экспорт данных за год

```
Пользователь: /report
Бот: Выберите период
     [День] [Неделя] [Месяц] [Произвольный]

Пользователь: [Месяц]
Бот: Выберите формат
     [📊 Excel] [📄 PDF]

Пользователь: [📊 Excel]
Бот: ⏳ Генерирую отчёт за февраль 2026...
     ✅ Отчёт готов!
     [отправка файла expenses_2026_02.xlsx]
```

### Структура Excel отчёта

**Лист 1: Сводка**
| Показатель | Значение |
|------------|----------|
| Общий доход | 50,000 RUB |
| Общий расход | 37,550 RUB |
| Баланс | +12,450 RUB |
| Отправлено переводов | 8,000 RUB |
| Получено переводов | 5,000 RUB |

**Лист 2: Транзакции**
| Дата | Тип | Категория | Сумма | Описание |
|------|-----|-----------|-------|----------|
| 01.02.2026 | Доход | Зарплата | 50,000 | Февраль |
| 03.02.2026 | Расход | Еда | 1,250 | Продукты |
| ... | ... | ... | ... | ... |

**Лист 3: Категории**
| Категория | Кол-во | Сумма | % |
|-----------|--------|-------|---|
| 🍔 Еда | 28 | 15,200 | 40.5% |
| 🏠 Жильё | 2 | 12,000 | 32.0% |
| ... | ... | ... | ... |

---

## Пример 5: Edge Cases

### 5.1 Недостаточно средств

```
Пользователь: ➖ Расход
Бот: Введите сумму

Пользователь: 15000
Бот: ❌ Недостаточно средств
     Ваш баланс: 5000 RUB
     Попытка расхода: 15000 RUB
```

### 5.2 Попытка перевода самому себе

```
Пользователь: /transfer
Бот: Введите @username

Пользователь: @myself
Бот: ❌ Нельзя перевести деньги самому себе
     Введите другой username
```

### 5.3 Получатель не зарегистрирован

```
Пользователь: /transfer
Бот: Введите @username

Пользователь: @unknown_user
Бот: ❌ Пользователь @unknown_user не найден
     Попросите его запустить бота: @expenses_bot
     [Отправить приглашение]
```

### 5.4 Отмена перевода с частичным расходом

```
Отправитель: /transfers
Бот: [список переводов]

Отправитель: [выбирает перевод к @bob]
Бот: Детали перевода
     Сумма: 5000 RUB
     Потрачено: 2000 RUB
     Остаток: 3000 RUB

Отправитель: [❌ Отменить перевод]
Бот: ⚠️ @bob уже потратил 2000 RUB
     Вернуть остаток (3000 RUB)?
     [Да, вернуть] [Отмена]

Отправитель: [Да, вернуть]
Бот: ✅ 3000 RUB возвращены на ваш счёт
     Перевод частично отменён
```

---

## Пример 6: API Integration (Future)

### Webhook для уведомлений

```python
# Настройка webhook
import httpx

webhook_url = "https://myapp.com/api/expenses-notification"

await set_user_webhook(
    user_id=123456789,
    url=webhook_url,
    events=["transfer_received", "transfer_spent"]
)
```

### Получение уведомления

```json
POST https://myapp.com/api/expenses-notification

{
    "event": "transfer_spent",
    "timestamp": "2026-02-11T14:30:00Z",
    "data": {
        "sender_id": 111111111,
        "recipient_id": 222222222,
        "recipient_username": "son",
        "amount": 3500.00,
        "currency": "RUB",
        "category": "Еда",
        "description": "Продукты на неделю",
        "remaining": 6500.00,
        "transfer_id": "uuid-here"
    }
}
```

---

## Пример 7: Мультивалютность

```
Пользователь: /settings
Бот: [меню настроек]

Пользователь: [💱 Валюта]
Бот: Выберите валюту по умолчанию
     [RUB] [USD] [EUR] [KZT] [UZS]

Пользователь: [USD]
Бот: ✅ Валюта изменена на USD

---

Пользователь: ➖ Расход
Бот: Введите сумму расхода (USD)

Пользователь: 50
Бот: ✅ Расход 50 USD добавлен
     Баланс: 420 USD
```

### Конвертация при переводе

```
Отправитель (USD): /transfer
Бот: Введите @username

Отправитель: @recipient_rub
Бот: Введите сумму

Отправитель: 100
Бот: ⚠️ Получатель использует RUB
     Конвертировать 100 USD в RUB по курсу 92.50?
     100 USD = 9,250 RUB
     [Подтвердить] [Отмена]
```

---

## Пример 8: Настройка уведомлений

```
Пользователь: /notifications
Бот: Настройки уведомлений

     🔔 Ежедневное напоминание: ВКЛ
     Время: 20:00
     [Изменить время] [Выключить]

     🔔 Получен перевод: ВКЛ
     [Выключить]

     🔔 Потрачены средства из перевода: ВКЛ
     [Выключить]

     🔔 Превышение бюджета: ВЫКЛ
     [Включить]
```

---

## Полезные команды

```bash
# Показать баланс
/balance

# Быстрое добавление расхода
/expense

# Статистика за текущий месяц
/stats

# Список отправленных переводов
/transfers

# Список полученных переводов
/received

# Отменить текущую операцию
/cancel

# Вернуться в главное меню
/menu
```

---

## 🔗 Связанные документы

- [README.md](README.md) - Основная документация
- [ARCHITECTURE.md](ARCHITECTURE.md) - Архитектура системы
- [API.md](API.md) - API документация
- [QUICK_START.md](QUICK_START.md) - Быстрый старт
