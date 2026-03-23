# 🚀 Запуск Telegram Mini App

## Предварительные требования

- Node.js 18+ и npm/yarn
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

## 📦 Установка зависимостей

### Frontend (React Mini App)

```bash
cd miniapp
npm install
```

### Backend (FastAPI)

```bash
pip install -r requirements.txt
```

## ⚙️ Настройка

### 1. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
BOT_USERNAME=your_bot_username

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=expenses_bot
DB_USER=expenses_user
DB_PASSWORD=your_db_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Configuration
API_BASE_URL=http://localhost:8000/api
```

### 2. Настройка Mini App URL

В файле `miniapp/src/api/client.ts` укажите URL вашего API:

```typescript
const apiClient = axios.create({
  baseURL: process.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
})
```

Создайте файл `miniapp/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 3. Регистрация Mini App в BotFather

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/mybots`
3. Выберите вашего бота
4. Нажмите **Menu Button** → **Edit Menu Button**
5. Введите URL вашего Mini App (после деплоя на хостинг)

## 🏃‍♂️ Запуск локально

### Вариант 1: Запуск компонентов по отдельности

#### 1. База данных и Redis

```bash
# Запуск PostgreSQL и Redis через Docker
docker-compose up postgres redis -d

# Применение миграций
cd database
psql -h localhost -U expenses_user -d expenses_bot -f schema.sql
```

#### 2. FastAPI Backend

```bash
# Запуск API сервера
python api_server.py
```

API будет доступно по адресу: `http://localhost:8000`
Документация: `http://localhost:8000/docs`

#### 3. React Frontend (Dev Server)

```bash
cd miniapp
npm run dev
```

Mini App будет доступно по адресу: `http://localhost:3000`

#### 4. Telegram Bot

```bash
python main.py
```

### Вариант 2: Запуск через Docker Compose

```bash
# Запуск всех сервисов одновременно
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down
```

## 🔧 Разработка

### Структура Mini App

```
miniapp/
├── public/              # Статические файлы
│   └── index.html       # HTML точка входа
├── src/
│   ├── api/             # API клиент и эндпоинты
│   │   ├── client.ts
│   │   └── endpoints.ts
│   ├── components/      # React компоненты
│   │   ├── Dashboard.tsx
│   │   ├── Transactions.tsx
│   │   ├── Transfers.tsx
│   │   ├── Statistics.tsx
│   │   ├── Settings.tsx
│   │   └── shared/
│   │       └── BottomNav.tsx
│   ├── hooks/           # Custom hooks
│   │   └── useTelegram.ts
│   ├── App.tsx          # Главный компонент
│   ├── main.tsx         # Точка входа React
│   └── index.css        # Глобальные стили
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

### Доступные команды

```bash
# Разработка
npm run dev         # Запуск dev сервера с hot reload

# Сборка
npm run build       # Сборка production версии
npm run preview     # Предпросмотр production сборки

# Линтинг
npm run lint        # Проверка кода ESLint
```

## 📱 Тестирование в Telegram

### Локальное тестирование через ngrok

1. Установите [ngrok](https://ngrok.com/download)

2. Запустите все сервисы локально

3. Создайте туннель для Mini App:
```bash
ngrok http 3000
```

4. Создайте туннель для API:
```bash
ngrok http 8000
```

5. Обновите URL в настройках:
   - В `miniapp/.env`: `VITE_API_BASE_URL=https://your-api-tunnel.ngrok.io/api`
   - В BotFather: укажите `https://your-miniapp-tunnel.ngrok.io`

6. Откройте бота в Telegram и нажмите кнопку **📱 Открыть Mini App**

## 🌐 Деплой на Production

### Frontend (Mini App)

Рекомендуемые платформы:
- **Vercel** (рекомендуется)
- **Netlify**
- **GitHub Pages**
- **Cloudflare Pages**

#### Деплой на Vercel

```bash
cd miniapp

# Установка Vercel CLI
npm i -g vercel

# Деплой
vercel --prod
```

Настройте переменные окружения в Vercel:
- `VITE_API_BASE_URL`: URL вашего API

### Backend (FastAPI)

Рекомендуемые платформы:
- **Railway** (рекомендуется)
- **Render**
- **DigitalOcean App Platform**
- **AWS EC2** / **VPS**

#### Деплой на Railway

1. Создайте проект на [Railway](https://railway.app)
2. Подключите GitHub репозиторий
3. Добавьте PostgreSQL и Redis из Marketplace
4. Настройте переменные окружения
5. Деплой произойдёт автоматически

### Telegram Bot

Запустите бота на сервере:

```bash
# Через Docker Compose
docker-compose up -d bot

# Или через systemd service
sudo systemctl start expenses-bot
```

## 🔒 Безопасность

### Проверка подписи Telegram

FastAPI автоматически проверяет подпись данных от Telegram WebApp:

```python
# api/middleware/telegram_auth.py
def verify_telegram_data(init_data: str) -> dict:
    # Проверка HMAC-SHA256 подписи
    # Подробнее: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
```

### CORS настройки

В production обязательно ограничьте CORS:

```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-miniapp-domain.com"],  # Только ваш домен
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## 📊 Мониторинг

### API Метрики

FastAPI предоставляет автоматическую документацию:
- Swagger UI: `http://your-api-domain.com/docs`
- ReDoc: `http://your-api-domain.com/redoc`

### Логирование

Логи сохраняются в директории `logs/`:
```
logs/
├── api.log           # API логи
├── bot.log           # Bot логи
└── celery.log        # Celery логи
```

## 🐛 Отладка

### Проверка подключения к API

```bash
# Проверка health check
curl http://localhost:8000/health

# Тест аутентификации
curl -H "X-Telegram-Init-Data: query_id=..." http://localhost:8000/api/auth/validate
```

### React DevTools

Установите [React Developer Tools](https://react.dev/learn/react-developer-tools) для отладки компонентов.

### Telegram WebApp Debugging

Для отладки в Telegram Desktop:
1. Откройте Settings → Advanced → Experimental settings
2. Включите "Enable webview inspecting"
3. Правый клик на Mini App → Inspect

## 📚 Дополнительные ресурсы

- [Telegram Mini Apps Documentation](https://core.telegram.org/bots/webapps)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [Vite Documentation](https://vitejs.dev/)

## ❓ FAQ

### Ошибка "Invalid hash" при авторизации

Убедитесь, что:
1. BOT_TOKEN в `.env` совпадает с токеном бота
2. Данные передаются через заголовок `X-Telegram-Init-Data`
3. Приложение открывается через официального бота

### Mini App не открывается

Проверьте:
1. URL Mini App зарегистрирован в BotFather
2. HTTPS используется в production
3. CORS настроен правильно

### Стили не применяются

Убедитесь, что:
1. TailwindCSS правильно настроен в `tailwind.config.js`
2. `index.css` импортирован в `main.tsx`
3. PostCSS плагины установлены

## 🤝 Поддержка

Если у вас возникли проблемы:
1. Проверьте логи: `docker-compose logs -f`
2. Изучите [документацию](./docs/)
3. Создайте issue в репозитории
