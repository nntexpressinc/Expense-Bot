# 🌐 Telegram Mini App для Expenses Bot

Web-интерфейс внутри Telegram для удобного управления финансами.

## 📱 Возможности Mini App

### Главный экран
- 💰 Текущий баланс (общий/свой/полученный)
- 📊 График доходов и расходов за месяц
- 🔝 Топ-3 категории расходов
- ⚡ Быстрые действия (доход/расход/перевод)

### Транзакции
- 📋 История всех операций с фильтрами
- ➕ Быстрое добавление дохода/расхода
- 🔍 Поиск по описанию
- 📅 Фильтр по датам и категориям

### Переводы
- 📤 Мои отправленные переводы
- 📥 Полученные переводы
- 💸 Создание нового перевода
- 📊 Детальная информация с графиками расходов

### Статистика
- 📈 Интерактивные графики
- 🗓️ Выбор периода (день/неделя/месяц/год)
- 📊 Круговая диаграмма категорий
- 💹 Динамика доходов и расходов

### Настройки
- 💱 Выбор валюты
- 🌐 Язык интерфейса
- 📂 Управление категориями
- 🔔 Настройки уведомлений
- 📄 Экспорт данных

---

## 🏗️ Технологии

### Frontend
- **React 18** + TypeScript
- **Vite** - быстрая сборка
- **Telegram WebApp API** - интеграция с Telegram
- **Recharts** - графики и диаграммы
- **TailwindCSS** - стилизация
- **React Query** - кэширование данных
- **Zustand** - state management

### Backend API
- **FastAPI** - REST API для Mini App
- **JWT** - авторизация через Telegram
- **CORS** - настройка для безопасности
- **WebSocket** - real-time обновления (опционально)

---

## 📂 Структура проекта

```
expenses-bot/
├── miniapp/                    # Telegram Mini App
│   ├── public/
│   │   ├── index.html
│   │   └── manifest.json
│   │
│   ├── src/
│   │   ├── components/        # React компоненты
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Transfers.tsx
│   │   │   ├── Statistics.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── shared/
│   │   │
│   │   ├── hooks/            # Custom hooks
│   │   │   ├── useTelegram.ts
│   │   │   ├── useTransactions.ts
│   │   │   └── useBalance.ts
│   │   │
│   │   ├── api/              # API клиент
│   │   │   ├── client.ts
│   │   │   └── endpoints.ts
│   │   │
│   │   ├── store/            # Zustand store
│   │   │   └── store.ts
│   │   │
│   │   ├── types/            # TypeScript types
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/            # Utilities
│   │   │   └── formatters.ts
│   │   │
│   │   ├── App.tsx           # Root component
│   │   └── main.tsx          # Entry point
│   │
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tailwind.config.js
│
└── api/                       # FastAPI backend
    ├── __init__.py
    ├── main.py               # FastAPI app
    ├── routers/
    │   ├── auth.py           # Telegram auth
    │   ├── transactions.py
    │   ├── transfers.py
    │   ├── statistics.py
    │   └── settings.py
    ├── middleware/
    │   └── telegram_auth.py
    └── schemas/
        └── api_models.py
```

---

## 🚀 Запуск Mini App

### Development

```bash
# Backend API
cd api
pip install fastapi uvicorn python-jose
uvicorn main:app --reload --port 8000

# Frontend
cd miniapp
npm install
npm run dev
```

### Production

```bash
# Build frontend
cd miniapp
npm run build

# Serve through nginx
# Backend API через FastAPI
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Добавлено в docker-compose.yml
docker-compose up -d
```

---

## 🔐 Безопасность

### Telegram WebApp Authentication

```typescript
// Проверка initData от Telegram
const validateTelegramWebAppData = (initData: string): boolean => {
  // Валидация подписи через crypto.createHmac
  // Использование bot token как secret
  return isValid;
}
```

### JWT токены
- Access token (15 мин)
- Refresh token (7 дней)
- HttpOnly cookies для безопасности

---

## 📱 Скриншоты интерфейса

### Главный экран
```
┌─────────────────────────────┐
│  💰 Expenses Bot            │
├─────────────────────────────┤
│                             │
│  Общий баланс               │
│  ₽ 12,450.00                │
│                             │
│  Свои средства: ₽9,450      │
│  Получено: ₽3,000           │
│                             │
│  📊 Февраль 2026            │
│  ┌─────────────────────┐   │
│  │   [График]          │   │
│  └─────────────────────┘   │
│                             │
│  🔝 Топ категории           │
│  🍔 Еда      ₽15,200 40%    │
│  🏠 Жильё    ₽12,000 32%    │
│  🚕 Транспорт ₽6,500 17%    │
│                             │
│  ⚡ Быстрые действия         │
│  [➕ Доход] [➖ Расход]      │
│  [💸 Перевод]               │
│                             │
└─────────────────────────────┘
```

---

## 🎨 UI/UX особенности

### Адаптивный дизайн
- Оптимизирован для мобильных устройств
- Поддержка темной темы Telegram
- Плавные анимации и transitions

### Жесты
- Swipe для удаления транзакций
- Pull-to-refresh для обновления данных
- Long press для дополнительных действий

### Haptic Feedback
```typescript
Telegram.WebApp.HapticFeedback.impactOccurred('light')
Telegram.WebApp.HapticFeedback.notificationOccurred('success')
```

---

## 📊 Возможности vs Бот

| Функция | Bot | Mini App | Преимущество |
|---------|-----|----------|-------------|
| Добавить расход | ✅ | ✅ | Mini App: быстрее |
| Просмотр истории | ⚠️ | ✅ | Mini App: удобнее |
| Графики | ❌ | ✅ | Только Mini App |
| Фильтры | ❌ | ✅ | Только Mini App |
| Уведомления | ✅ | ❌ | Только Bot |
| Offline режим | ❌ | ⚠️ | Mini App: PWA |

---

## 🔗 Интеграция с ботом

### Открытие Mini App из бота

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

def get_miniapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url="https://expenses-bot.example.com")
        )
    ]])
```

### Callback из Mini App в бот

```typescript
// Отправка данных в бот
Telegram.WebApp.sendData(JSON.stringify({
  action: 'transaction_created',
  amount: 500,
  category: 'food'
}))
```

---

## 🚀 Roadmap Mini App

### v1.0
- ✅ Основные экраны (Dashboard, Transactions)
- ✅ Добавление транзакций
- ✅ Просмотр баланса и истории
- ✅ Базовые графики

### v1.1
- 📊 Интерактивные графики (Recharts)
- 🔍 Продвинутые фильтры
- 📥 Импорт/Экспорт данных
- 🌓 Темная тема

### v1.2
- 💸 Управление переводами
- 📸 Сканирование чеков (OCR)
- 🗺️ Карта расходов (геолокация)
- 📱 PWA (работа offline)

### v2.0
- 🤖 AI-ассистент для анализа
- 📈 Прогнозы расходов
- 👥 Общие бюджеты
- 🎮 Gamification

---

## 📖 Документация

См. также:
- [MINIAPP_API.md](MINIAPP_API.md) - API документация
- [MINIAPP_COMPONENTS.md](MINIAPP_COMPONENTS.md) - Компоненты React
- [MINIAPP_SETUP.md](MINIAPP_SETUP.md) - Настройка и деплой
