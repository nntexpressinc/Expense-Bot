# Docker orqali Test Qilish Yo'riqnomasi

## Tezkor Boshlash (Quick Start)

### 1. Tayyorgarlik

```powershell
# Loyiha papkasiga kirish
cd C:\Users\Xolmirza\Desktop\expenses-bot

# .env faylini tekshirish (muhim!)
# TELEGRAM_BOT_TOKEN to'g'ri sozlanganligini tekshiring
```

### 2. Docker Compose bilan ishga tushirish

```powershell
# Barcha servicelarni build va run qilish
docker-compose up --build

# Yoki background da ishga tushirish
docker-compose up -d --build
```

Bu quyidagilarni ishga tushiradi:
- ✅ PostgreSQL database (port 5432)
- ✅ Redis (port 6379)
- ✅ Telegram Bot
- ✅ API Server (port 8000)
- ✅ Celery Worker (background tasks)
- ✅ Celery Beat (scheduled tasks)

---

## To'liq Test Qilish (Step-by-Step)

### Qadam 1: Environment Variables Tekshirish

`.env` faylini oching va quyidagilarni to'g'rilang:

```env
# Bot token (MAJBURIY)
TELEGRAM_BOT_TOKEN=8398797031:AAG6sxlQJ70vFIjGFxEvs7RViBCu6TB0okI

# Database (default sozlamalar yaxshi)
DATABASE_URL=postgresql+asyncpg://expenses_user:change_me_in_production@postgres:5432/expenses_bot

# Redis (default sozlamalar yaxshi)
REDIS_URL=redis://redis:6379/0

# Webhook o'chirilgan - polling ishlaydi
USE_WEBHOOK=false

# Mini App URL (hozircha bo'sh qoldiring)
MINIAPP_URL=

# Debug mode yoqilgan
DEBUG=True
```

### Qadam 2: Docker Containerlarni Ishga Tushirish

```powershell
# Barcha servicelarni background da ishga tushirish
docker-compose up -d

# Loglarni ko'rish
docker-compose logs -f

# Yoki faqat bot loglarini ko'rish
docker-compose logs -f bot

# Yoki faqat API loglarini ko'rish
docker-compose logs -f api
```

### Qadam 3: Servicelar Holatini Tekshirish

```powershell
# Barcha containerlar ishga tushganini tekshirish
docker-compose ps

# Database connection tekshirish
docker-compose exec postgres psql -U expenses_user -d expenses_bot -c "SELECT 1;"

# Redis connection tekshirish
docker-compose exec redis redis-cli ping

# API server tekshirish
curl http://localhost:8000/api/health
# yoki PowerShell da:
Invoke-WebRequest -Uri http://localhost:8000/api/health
```

### Qadam 4: Bot Ishlayotganini Tekshirish

Telegram da botingizni oching va quyidagi komandalarni sinab ko'ring:

1. ✅ `/start` - Bot javob beradimi?
2. ✅ `/help` - Help matni to'g'rimi?
3. ✅ `➕ Доход` tugmasi - Income qo'shish ishlayaptimi?
4. ✅ `➖ Расход` tugmasi - Expense qo'shish ishlayaptimi?
5. ✅ `📊 Статистика` tugmasi - Stats ko'rsatyaptimi?
6. ✅ `⚙️ Настройки` tugmasi - Settings ochilmoqdami?

### Qadam 5: Database Ma'lumotlarini Tekshirish

```powershell
# Database ga kirish
docker-compose exec postgres psql -U expenses_user -d expenses_bot

# SQL komandalar:
# Userlarni ko'rish
SELECT * FROM users;

# Transactionlarni ko'rish
SELECT * FROM transactions;

# Chiqish
\q
```

### Qadam 6: API Endpoints Tekshirish

```powershell
# Health check
curl http://localhost:8000/api/health

# API documentation (browser da oching)
# http://localhost:8000/docs

# Yoki PowerShell da:
Invoke-WebRequest -Uri http://localhost:8000/docs
```

---

## Mini App ni Docker bilan Test Qilish

### Variant 1: Mini App ni alohida ishga tushirish (Tavsiya)

```powershell
# Yangi terminal oching
cd C:\Users\Xolmirza\Desktop\expenses-bot\miniapp

# Dependencies o'rnatish
npm install

# Development server ishga tushirish
npm run dev
```

Mini app `http://localhost:5173` da ochiladi.

### Variant 2: Ngrok bilan HTTPS URL olish

Telegram Mini App uchun HTTPS kerak:

```powershell
# Terminal 1: Mini app ishga tushiring
cd miniapp
npm run dev

# Terminal 2: Ngrok ishga tushiring
ngrok http 5173
```

Ngrok URL ni `.env` ga qo'shing:
```env
MINIAPP_URL=https://your-ngrok-url.ngrok-free.app
```

Containerlarni qayta ishga tushiring:
```powershell
docker-compose restart bot
```

---

## Debug va Troubleshooting

### Container ishga tushmasa:

```powershell
# Containerlar holatini tekshirish
docker-compose ps

# Barcha loglarni ko'rish
docker-compose logs

# Muayyan service logini ko'rish
docker-compose logs bot
docker-compose logs api
docker-compose logs postgres

# Container ichiga kirish (debug uchun)
docker-compose exec bot sh
docker-compose exec postgres sh
```

### Database bilan muammo bo'lsa:

```powershell
# Database ni reset qilish (DIQQAT: barcha ma'lumotlar o'chadi!)
docker-compose down -v
docker-compose up -d

# Database migration tekshirish
docker-compose exec bot python -c "from database.session import init_db; import asyncio; asyncio.run(init_db())"
```

### Port band bo'lsa:

`.env` faylida portlarni o'zgartiring yoki `docker-compose.yml` da:

```yaml
ports:
  - "5433:5432"  # PostgreSQL uchun boshqa port
  - "8001:8000"  # API uchun boshqa port
```

### Bot javob bermasa:

1. Bot token to'g'ri sozlanganligini tekshiring
2. Internet aloqasi mavjudligini tekshiring
3. Bot loglarini ko'ring:
   ```powershell
   docker-compose logs -f bot
   ```

---

## Foydali Docker Komandalar

```powershell
# Barcha containerlarni to'xtatish
docker-compose stop

# Barcha containerlarni o'chirish
docker-compose down

# Barcha containerlar va volumelarni o'chirish (ma'lumotlar ham)
docker-compose down -v

# Containerlarni qayta ishga tushirish
docker-compose restart

# Yangi build qilish
docker-compose build --no-cache

# Bitta serviceni alohida ishga tushirish
docker-compose up bot

# Container ichiga kirish (bash/sh)
docker-compose exec bot sh
docker-compose exec postgres bash

# Container loglarini real-time ko'rish
docker-compose logs -f --tail=100 bot

# Resource usage ko'rish
docker stats
```

---

## Test Checklist

### Bot Funksiyalari:
- [ ] `/start` komandasi ishlaydi
- [ ] `/help` to'g'ri ma'lumot ko'rsatadi
- [ ] Income qo'shish ishlaydi
- [ ] Expense qo'shish ishlaydi
- [ ] Balance to'g'ri hisoblanyapti
- [ ] Statistics ko'rsatyapti
- [ ] Transfer funksiyasi ishlaydi
- [ ] Settings ochilmoqda
- [ ] Language o'zgartirish ishlaydi
- [ ] Currency o'zgartirish ishlaydi

### API Endpoints:
- [ ] `http://localhost:8000/docs` ochilmoqda
- [ ] Health check ishlayapti
- [ ] Authentication ishlayapti
- [ ] CRUD operatsiyalar ishlayapti

### Database:
- [ ] PostgreSQL ishga tushdi
- [ ] Tables yaratildi
- [ ] Ma'lumotlar saqlanmoqda
- [ ] Backup olinadi

### Infrastructure:
- [ ] Barcha containerlar ishga tushdi (6 ta)
- [ ] Health checks o'tmoqda
- [ ] Loglar to'g'ri yozilmoqda
- [ ] Volume mount ishlayapti

---

## Production ga Deployment

Production serverda:

```bash
# Server da
cd /var/www/expenses-bot

# Environment variables sozlash
nano .env
# DEBUG=False
# USE_WEBHOOK=true
# TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook

# Docker Compose bilan ishga tushirish
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# SSL sozlash (Nginx + Let's Encrypt)
# Nginx config yozish
# Certbot bilan SSL olish
```

---

## Monitoring

```powershell
# Container resource usage
docker stats

# Disk usage
docker system df

# Loglarni export qilish
docker-compose logs --no-color > logs/all-services.log

# Database backup
docker-compose exec postgres pg_dump -U expenses_user expenses_bot > backup.sql

# Database restore
docker-compose exec -T postgres psql -U expenses_user expenses_bot < backup.sql
```

---

## Tez-tez So'raladigan Savollar

**Q: Docker Desktop kerakmi?**
A: Windows da ha, Docker Desktop o'rnatilgan bo'lishi kerak.

**Q: Port 5432 band deyapti?**
A: PostgreSQL allaqachon o'rnatilgan bo'lsa, `docker-compose.yml` da portni o'zgartiring: `"5433:5432"`

**Q: Bot ishlamayapti?**
A: 
1. Bot token to'g'riligini tekshiring
2. `docker-compose logs bot` ni ko'ring
3. Internet aloqasini tekshiring

**Q: Database ma'lumotlari o'chib ketadimi?**
A: Yo'q, `docker-compose down` qilsangiz ham ma'lumotlar saqlanadi. Faqat `docker-compose down -v` bilan volumelar o'chadi.

**Q: Mini app ni qanday test qilaman?**
A: Mini app ni alohida `npm run dev` bilan ishga tushiring, keyin Ngrok bilan HTTPS URL oling.

---

## Qo'shimcha Manbalar

- Docker Docs: https://docs.docker.com
- Docker Compose: https://docs.docker.com/compose
- PostgreSQL Docker: https://hub.docker.com/_/postgres
- Redis Docker: https://hub.docker.com/_/redis

---

**Hozir boshla! 🚀**

```powershell
cd C:\Users\Xolmirza\Desktop\expenses-bot
docker-compose up -d
docker-compose logs -f bot
```

Telegram da botni oching va `/start` yuboring!
