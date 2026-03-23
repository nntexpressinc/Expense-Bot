# 📖 Примеры использования Mini App API

## Аутентификация

Все запросы к API должны содержать заголовок `X-Telegram-Init-Data` с данными от Telegram WebApp.

```typescript
// Автоматически добавляется в клиенте
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
})

apiClient.interceptors.request.use((config) => {
  const initData = window.Telegram?.WebApp?.initData
  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData
  }
  return config
})
```

## 🔐 Auth Endpoints

### Проверка валидности токена

```http
GET /api/auth/validate
```

**Response:**
```json
{
  "valid": true,
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "John"
  }
}
```

## 💰 Balance Endpoint

### Получить баланс

```http
GET /api/settings/balance
```

**Response:**
```json
{
  "total_balance": 150000.00,
  "own_balance": 100000.00,
  "received_balance": 50000.00,
  "currency": "RUB"
}
```

## 📋 Transactions Endpoints

### Получить список транзакций

```http
GET /api/transactions?type=expense&limit=20&offset=0
```

**Parameters:**
- `type` (optional): `income` или `expense`
- `limit` (optional): количество записей (default: 20, max: 100)
- `offset` (optional): смещение для пагинации (default: 0)

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "expense",
    "amount": 1500.00,
    "currency": "RUB",
    "category": {
      "id": 3,
      "name": "Продукты",
      "icon": "🛒"
    },
    "description": "Покупки в Пятёрочке",
    "transaction_date": "2024-01-15T14:30:00"
  }
]
```

### Создать транзакцию

```http
POST /api/transactions
Content-Type: application/json
```

**Body:**
```json
{
  "type": "expense",
  "amount": 1500.00,
  "currency": "RUB",
  "category_id": 3,
  "description": "Покупки в Пятёрочке"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "expense",
  "amount": 1500.00,
  "currency": "RUB",
  "category": {
    "id": 3,
    "name": "Продукты",
    "icon": "🛒"
  },
  "description": "Покупки в Пятёрочке",
  "transaction_date": "2024-01-15T14:30:00"
}
```

### Удалить транзакцию

```http
DELETE /api/transactions/{transaction_id}
```

**Response:**
```json
{
  "message": "Transaction deleted successfully"
}
```

## 💸 Transfers Endpoints

### Получить отправленные переводы

```http
GET /api/transfers/sent?limit=20&offset=0
```

**Response:**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "sender_id": 1,
    "recipient_id": 2,
    "recipient_username": "jane_doe",
    "amount": 5000.00,
    "remaining_amount": 2000.00,
    "currency": "RUB",
    "status": "completed",
    "description": "На продукты",
    "created_at": "2024-01-10T12:00:00"
  }
]
```

### Получить полученные переводы

```http
GET /api/transfers/received?limit=20&offset=0
```

**Response:** аналогичен отправленным переводам

### Создать перевод

```http
POST /api/transfers
Content-Type: application/json
```

**Body:**
```json
{
  "recipient_telegram_id": 987654321,
  "amount": 5000.00,
  "currency": "RUB",
  "description": "На продукты"
}
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "sender_id": 1,
  "recipient_id": 2,
  "recipient_username": "jane_doe",
  "amount": 5000.00,
  "remaining_amount": 5000.00,
  "currency": "RUB",
  "status": "pending",
  "description": "На продукты",
  "created_at": "2024-01-10T12:00:00"
}
```

### Получить детали перевода

```http
GET /api/transfers/{transfer_id}
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "sender_id": 1,
  "recipient_id": 2,
  "recipient_username": "jane_doe",
  "amount": 5000.00,
  "remaining_amount": 2000.00,
  "currency": "RUB",
  "status": "completed",
  "description": "На продукты",
  "created_at": "2024-01-10T12:00:00",
  "expenses": [
    {
      "id": 1,
      "amount": 1500.00,
      "category": {
        "id": 3,
        "name": "Продукты",
        "icon": "🛒"
      },
      "description": "Пятёрочка",
      "created_at": "2024-01-11T14:30:00"
    },
    {
      "id": 2,
      "amount": 1500.00,
      "category": {
        "id": 3,
        "name": "Продукты",
        "icon": "🛒"
      },
      "description": "Магнит",
      "created_at": "2024-01-12T18:20:00"
    }
  ]
}
```

## 📊 Statistics Endpoint

### Получить статистику

```http
GET /api/statistics?period=month
```

**Parameters:**
- `period`: `day`, `week`, `month`, или `year`

**Response:**
```json
{
  "period": "Январь 2024",
  "total_income": 120000.00,
  "total_expense": 85000.00,
  "difference": 35000.00,
  "top_categories": [
    {
      "id": 3,
      "name": "Продукты",
      "icon": "🛒",
      "amount": 25000.00,
      "percent": 29.4
    },
    {
      "id": 5,
      "name": "Транспорт",
      "icon": "🚗",
      "amount": 15000.00,
      "percent": 17.6
    },
    {
      "id": 8,
      "name": "Развлечения",
      "icon": "🎬",
      "amount": 12000.00,
      "percent": 14.1
    }
  ]
}
```

## 🏷️ Settings Endpoints

### Получить категории

```http
GET /api/settings/categories?type=expense
```

**Parameters:**
- `type` (optional): `income` или `expense`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Зарплата",
    "type": "income",
    "icon": "💰",
    "is_system": true
  },
  {
    "id": 3,
    "name": "Продукты",
    "type": "expense",
    "icon": "🛒",
    "is_system": true
  }
]
```

## 🔄 Примеры использования в React

### Получение баланса с React Query

```typescript
import { useQuery } from '@tanstack/react-query'
import { getBalance } from '@/api/endpoints'

function BalanceCard() {
  const { data: balance, isLoading, error } = useQuery({
    queryKey: ['balance'],
    queryFn: getBalance,
    refetchInterval: 30000, // Обновлять каждые 30 секунд
  })

  if (isLoading) return <div>Загрузка...</div>
  if (error) return <div>Ошибка загрузки</div>

  return (
    <div>
      <h2>Баланс: {balance?.total_balance.toLocaleString()} ₽</h2>
    </div>
  )
}
```

### Создание транзакции с мутацией

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTransaction } from '@/api/endpoints'
import { useTelegram } from '@/hooks/useTelegram'

function AddExpenseForm() {
  const queryClient = useQueryClient()
  const { haptic } = useTelegram()

  const mutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: () => {
      // Обновляем кэш
      queryClient.invalidateQueries(['transactions'])
      queryClient.invalidateQueries(['balance'])
      queryClient.invalidateQueries(['statistics'])
      
      // Haptic feedback
      haptic.success()
      
      alert('Расход добавлен!')
    },
    onError: () => {
      haptic.error()
      alert('Ошибка при добавлении')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({
      type: 'expense',
      amount: 1500,
      currency: 'RUB',
      category_id: 3,
      description: 'Покупки'
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? 'Сохранение...' : 'Добавить'}
      </button>
    </form>
  )
}
```

### Бесконечная прокрутка транзакций

```typescript
import { useInfiniteQuery } from '@tanstack/react-query'
import { getTransactions } from '@/api/endpoints'

function TransactionsList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['transactions'],
    queryFn: ({ pageParam = 0 }) => 
      getTransactions({ limit: 20, offset: pageParam }),
    getNextPageParam: (lastPage, pages) => 
      lastPage.length === 20 ? pages.length * 20 : undefined,
  })

  return (
    <div>
      {data?.pages.map((page, i) => (
        <div key={i}>
          {page.map(transaction => (
            <TransactionCard key={transaction.id} data={transaction} />
          ))}
        </div>
      ))}
      
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? 'Загрузка...' : 'Загрузить ещё'}
        </button>
      )}
    </div>
  )
}
```

## 🚨 Обработка ошибок

### Коды ошибок

- **400** - Bad Request (неверные данные)
- **401** - Unauthorized (неверная подпись Telegram)
- **404** - Not Found (ресурс не найден)
- **422** - Validation Error (ошибка валидации Pydantic)
- **500** - Internal Server Error

### Пример обработки

```typescript
import { AxiosError } from 'axios'

try {
  const transaction = await createTransaction(data)
} catch (error) {
  if (error instanceof AxiosError) {
    if (error.response?.status === 401) {
      // Перезапустить приложение
      window.Telegram?.WebApp?.close()
    } else if (error.response?.status === 422) {
      // Показать ошибки валидации
      const errors = error.response.data.detail
      console.error('Validation errors:', errors)
    }
  }
}
```

## 🔒 Безопасность

### Проверка подписи

FastAPI автоматически проверяет подпись Telegram WebApp:

```python
# api/middleware/telegram_auth.py
def verify_telegram_data(init_data: str) -> dict:
    parsed_data = dict(parse_qsl(init_data))
    received_hash = parsed_data.pop('hash')
    
    # Создаём секретный ключ
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()
    
    # Вычисляем hash
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Проверяем
    if not hmac.compare_digest(received_hash, calculated_hash):
        raise HTTPException(status_code=401)
```

## 📚 Документация

Swagger UI доступен по адресу: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
