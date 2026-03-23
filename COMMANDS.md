# ⚡ Быстрые команды для запуска проекта

## 🚀 Первый запуск (с нуля)

```bash
# 1. Клонирование репозитория (если нужно)
git clone <repo-url>
cd expenses-bot

# 2. Настройка окружения
cp .env.example .env
# Отредактируйте .env файл!

# 3. Установка зависимостей Backend
pip install -r requirements.txt

# 4. Установка зависимостей Frontend
cd miniapp
npm install
cd ..

# 5. Запуск через Docker (рекомендуется)
docker-compose up -d

# 6. Проверка статуса
docker-compose ps

# 7. Просмотр логов
docker-compose logs -f
```

## 🐳 Docker команды

### Управление контейнерами

```bash
# Запустить все сервисы
docker-compose up -d

# Остановить все сервисы
docker-compose down

# Перезапустить все сервисы
docker-compose restart

# Запустить конкретный сервис
docker-compose up -d bot
docker-compose up -d api

# Остановить конкретный сервис
docker-compose stop bot

# Пересобрать образы
docker-compose build

# Пересобрать и запустить
docker-compose up -d --build
```

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f bot
docker-compose logs -f api
docker-compose logs -f postgres

# Последние 100 строк
docker-compose logs --tail=100 bot
```

### Проверка статуса

```bash
# Статус всех контейнеров
docker-compose ps

# Использование ресурсов
docker stats
```

### Очистка

```bash
# Остановить и удалить контейнеры
docker-compose down

# Удалить контейнеры и volumes
docker-compose down -v

# Полная очистка (ОСТОРОЖНО: удалит все данные!)
docker-compose down -v --rmi all
```

## 💻 Локальная разработка (без Docker)

### Backend

```bash
# Terminal 1: PostgreSQL
# Установите и запустите PostgreSQL локально

# Terminal 2: Redis
# Установите и запустите Redis локально

# Terminal 3: Bot
python main.py

# Terminal 4: API Server
python api_server.py

# Terminal 5: Celery Worker (опционально)
celery -A tasks.celery worker --loglevel=info

# Terminal 6: Celery Beat (опционально)
celery -A tasks.celery beat --loglevel=info
```

### Frontend (Mini App)

```bash
cd miniapp

# Development server (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🗄️ База данных

### Применение схемы

```bash
# Через Docker
docker exec -i expenses_bot_postgres psql -U expenses_user -d expenses_bot < database/schema.sql

# Локально
psql -h localhost -U expenses_user -d expenses_bot -f database/schema.sql
```

### Подключение к БД

```bash
# Через Docker
docker exec -it expenses_bot_postgres psql -U expenses_user -d expenses_bot

# Локально
psql -h localhost -U expenses_user -d expenses_bot
```

### Бэкап и восстановление

```bash
# Создать бэкап
docker exec expenses_bot_postgres pg_dump -U expenses_user expenses_bot > backup.sql

# Восстановить из бэкапа
docker exec -i expenses_bot_postgres psql -U expenses_user -d expenses_bot < backup.sql
```

## 🔍 Отладка

### Проверка API

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI
# Откройте в браузере: http://localhost:8000/docs

# ReDoc
# Откройте в браузере: http://localhost:8000/redoc
```

### Проверка подключений

```bash
# PostgreSQL
docker exec expenses_bot_postgres pg_isready -U expenses_user

# Redis
docker exec expenses_bot_redis redis-cli ping
```

### Просмотр логов приложений

```bash
# Логи в директории logs/
tail -f logs/bot.log
tail -f logs/api.log
tail -f logs/celery.log
```

## 🧪 Тестирование

### Backend тесты

```bash
# Запуск всех тестов
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный файл
pytest tests/test_handlers.py

# Конкретный тест
pytest tests/test_handlers.py::test_start_command
```

### Frontend тесты

```bash
cd miniapp

# Запуск тестов
npm test

# С покрытием
npm run test:coverage

# E2E тесты (если настроены)
npm run test:e2e
```

## 📦 Установка зависимостей

### Python (Backend)

```bash
# Основные зависимости
pip install -r requirements.txt

# Только для разработки
pip install -r requirements-dev.txt

# Обновить все зависимости
pip install --upgrade -r requirements.txt

# Добавить новую зависимость
pip install <package-name>
pip freeze > requirements.txt
```

### Node.js (Frontend)

```bash
cd miniapp

# Установка
npm install

# Добавить зависимость
npm install <package-name>

# Добавить dev зависимость
npm install --save-dev <package-name>

# Обновить зависимости
npm update

# Проверить устаревшие пакеты
npm outdated
```

## 🌐 Деплой

### Vercel (Frontend)

```bash
cd miniapp

# Установка Vercel CLI
npm i -g vercel

# Логин
vercel login

# Деплой
vercel --prod
```

### Railway (Backend)

```bash
# Установка Railway CLI
npm i -g @railway/cli

# Логин
railway login

# Инициализация проекта
railway init

# Деплой
railway up
```

### Manual (VPS)

```bash
# На сервере
git clone <repo-url>
cd expenses-bot

# Настройка
cp .env.example .env
nano .env

# Запуск
docker-compose up -d

# Настройка автозапуска
sudo systemctl enable docker
```

## 🔄 Git команды

### Ежедневная работа

```bash
# Проверка статуса
git status

# Добавить изменения
git add .

# Коммит
git commit -m "feat: добавлена новая функция"

# Push
git push origin main

# Pull последних изменений
git pull origin main

# Создать новую ветку
git checkout -b feature/new-feature

# Переключиться на ветку
git checkout main

# Список веток
git branch -a
```

### Работа с удалённым репозиторием

```bash
# Добавить remote
git remote add origin <repo-url>

# Посмотреть remotes
git remote -v

# Обновить remote
git fetch origin

# Merge изменений
git merge origin/main
```

## 🛠️ Полезные утилиты

### Мониторинг ресурсов

```bash
# CPU и Memory всех контейнеров
docker stats

# Использование диска
docker system df

# Подробная информация
docker system df -v
```

### Очистка Docker

```bash
# Удалить неиспользуемые images
docker image prune

# Удалить неиспользуемые volumes
docker volume prune

# Удалить всё неиспользуемое
docker system prune -a
```

## 📊 Celery (фоновые задачи)

### Запуск

```bash
# Worker
celery -A tasks.celery worker --loglevel=info

# Beat (scheduler)
celery -A tasks.celery beat --loglevel=info

# Flower (monitoring)
celery -A tasks.celery flower --port=5555
```

### Мониторинг

```bash
# Открыть Flower в браузере
# http://localhost:5555

# Статус задач
celery -A tasks.celery inspect active

# Зарегистрированные задачи
celery -A tasks.celery inspect registered
```

## 🔐 Безопасность

### Генерация секретных ключей

```bash
# Генерация случайного ключа
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Генерация UUID
python -c "import uuid; print(uuid.uuid4())"
```

### Проверка .env файла

```bash
# Убедитесь, что .env не попадёт в git
cat .gitignore | grep .env

# Проверка наличия всех переменных
diff .env.example .env
```

## 📝 Линтинг и форматирование

### Python

```bash
# Black (форматирование)
black .

# Flake8 (линтинг)
flake8 .

# isort (сортировка импортов)
isort .

# mypy (проверка типов)
mypy .
```

### TypeScript/JavaScript

```bash
cd miniapp

# ESLint
npm run lint

# Prettier
npm run format

# Type check
npm run type-check
```

## 🎯 Быстрые сценарии

### Полная перезагрузка

```bash
# Остановить всё
docker-compose down -v

# Пересобрать
docker-compose build

# Запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f
```

### Обновление после git pull

```bash
# Обновить код
git pull origin main

# Обновить зависимости
pip install -r requirements.txt
cd miniapp && npm install && cd ..

# Перезапустить
docker-compose restart
```

### Сброс базы данных

```bash
# ОСТОРОЖНО: Удалит все данные!
docker-compose down -v
docker-compose up -d postgres
sleep 5
docker exec -i expenses_bot_postgres psql -U expenses_user -d expenses_bot < database/schema.sql
docker-compose up -d
```

## 📚 Документация

```bash
# Открыть главную документацию
cat docs/README.md

# Быстрый старт
cat docs/QUICK_START.md

# Инструкции Mini App
cat MINIAPP_SETUP.md

# API примеры
cat docs/MINIAPP_API.md
```

## 🆘 Помощь

Если что-то не работает:

1. Проверьте логи: `docker-compose logs -f`
2. Проверьте статус: `docker-compose ps`
3. Проверьте .env файл
4. Проверьте порты: `netstat -tuln | grep -E '5432|6379|8000|3000'`
5. Перезапустите: `docker-compose restart`

Если проблема не решается:
- Создайте issue на GitHub
- Проверьте документацию
- Спросите в Telegram чате (если есть)
