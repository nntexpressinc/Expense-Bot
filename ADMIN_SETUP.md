# Admin Setup Guide / Admin sozlash qo'llanmasi

## 1. Admin ID ni topish va sozlash

### O'zingizning Telegram ID'ingizni topish:

**Usul 1: @userinfobot orqali**
1. Telegramda [@userinfobot](https://t.me/userinfobot) ni oching
2. `/start` ni bosing
3. Sizning ID'ingiz ko'rsatiladi (masalan: `123456789`)

**Usul 2: Bot log'laridan**
1. Botni ishga tushiring
2. Bot'ga `/start` yuboring
3. Terminal/console'da log'larni ko'ring, ID ko'rsatiladi

### `.env` faylga ID'ni qo'shish:

```env
# Admin Settings
ADMIN_USER_IDS=123456789
```

**Ko'p adminlar uchun (vergul bilan ajratish):**
```env
ADMIN_USER_IDS=123456789,987654321,555666777
```

## 2. Admin imkoniyatlari

### 2.1. Bot orqali (Telegram)

Admin'lar bot'da maxsus buyruqlarga kirish huquqiga ega:
- Valyuta kursini o'zgartirish
- Sozlamalar
- Statistika

### 2.2. Mini App orqali (Web Interface)

Admin'lar Mini App'da **Admin Panel**'ga kirish huquqiga ega.

**Qanday kirish:**
1. Mini App'ni oching
2. `Settings` (⚙️ Sozlamalar) ga o'ting
3. **Admin Panel** tugmasini bosing (faqat adminlar ko'radi)

**Admin Panel imkoniyatlari:**

#### 📊 Dashboard
- Umumiy foydalanuvchilar soni
- Faol foydalanuvchilar
- Jami tranzaksiyalar
- Jami o'tkazmalar
- Umumiy hajm (volume)

#### 👥 Users (Foydalanuvchilar)
- Barcha foydalanuvchilar ro'yxati
- Qidiruv funksiyasi
- Har bir foydalanuvchi uchun:
  - **Make Admin / Remove Admin** - admin qilish/admin'likni olish
  - **Active / Inactive** - faollashtirish/o'chirish

#### 💱 Exchange Rate (Valyuta kursi)
- Joriy USD → UZS kursini ko'rish
- Yangi kursni o'rnatish
- Real-time yangilanish

## 3. Adminlar'ni boshqarish

### Database orqali admin qo'shish:

```sql
-- User'ni admin qilish
UPDATE users SET is_admin = true WHERE id = 123456789;

-- Admin'likni olish
UPDATE users SET is_admin = false WHERE id = 123456789;
```

### Mini App orqali admin qo'shish:

1. Admin Panel → Users → Foydalanuvchini toping
2. "Make Admin" tugmasini bosing
3. Tasdiqlang

**Muhim:**
- O'zingizni admin'dan olib bo'lmaydi (xavfsizlik uchun)
- Kamida 1 ta admin bo'lishi kerak

## 4. Admin huquqlari va xavfsizlik

### Admin faqat qila oladigan ishlar:

**API Endpoints:**
- `GET /api/admin/stats` - Umumiy statistika
- `GET /api/admin/users` - Barcha foydalanuvchilar
- `GET /api/admin/users/{user_id}` - Foydalanuvchi tafsilotlari
- `PATCH /api/admin/users/{user_id}/admin` - Admin status o'zgartirish
- `PATCH /api/admin/users/{user_id}/activate` - Faollashtirish/o'chirish
- `DELETE /api/admin/users/{user_id}` - Foydalanuvchini o'chirish
- `PATCH /api/settings/exchange-rate/{from}/{to}` - Valyuta kursini yangilash

### Xavfsizlik qoidalari:

1. **`.env` faylni xavfsiz saqlang** - Token va admin ID'lar maxfiy
2. **Admin ID'larni ehtiyotkorlik bilan bering** - Faqat ishonchli odamlarga
3. **Production'da:** HTTPS ishlatish majburiy
4. **Loglarni tekshiring** - Kim qanday o'zgarishlar kiritganini kuzating

## 5. Docker bilan ishlatish

### Docker Compose bilan ishga tushirish:

```bash
# 1. .env faylda admin ID'ni to'g'ri qo'ying
nano .env

# 2. Docker container'larni ishga tushiring
docker-compose up -d

# 3. Log'larni ko'ring
docker-compose logs -f api

# 4. Container ichida database migration
docker-compose exec postgres psql -U expenses_user -d expenses_bot -f /migrations/001_add_exchange_rate_and_admin.sql
```

### Admin yaratish Docker orqali:

```bash
# Python shell ochish
docker-compose exec api python

# Python shell ichida:
>>> from database.session import SessionLocal
>>> from database.models import User
>>> from sqlalchemy import update
>>> 
>>> db = SessionLocal()
>>> db.execute(update(User).where(User.id == 123456789).values(is_admin=True))
>>> db.commit()
>>> db.close()
>>> exit()
```

## 6. Test qilish

### 1. Admin ekanligingizni tekshiring:

```bash
# API orqali
curl -X GET "http://localhost:8000/api/settings/user" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Natija:
{
  "id": 123456789,
  "username": "your_username",
  "first_name": "Your Name",
  "is_admin": true,  # ✅ Admin
  ...
}
```

### 2. Mini App'da admin panel ko'rinishini tekshiring:

1. Mini App'ni oching
2. Settings'ga o'ting
3. Admin Panel tugmasi ko'rinadi ✅

### 3. Valyuta kursini o'zgartirishni test qiling:

1. Admin Panel → Exchange tab
2. Yangi kursni kiriting (masalan: 12500)
3. "Update Exchange Rate" bosing
4. ✅ Success message ko'rinadi

## 7. Ko'p uchraydigan muammolar

### ❌ Admin Panel ko'rinmaydi
**Sabab:** `is_admin = false` yoki `.env` da ID yo'q

**Yechim:**
1. `.env` faylda `ADMIN_USER_IDS` ni tekshiring
2. Database'da `UPDATE users SET is_admin = true WHERE id = YOUR_ID`
3. Docker'ni restart qiling: `docker-compose restart api`

### ❌ "403 Admin access required" xatosi
**Sabab:** Admin huquqlari yo'q

**Yechim:**
- Telegram ID'ingiz to'g'ri ekanligini tekshiring
- `.env` faylda ID to'g'ri yozilganligini tekshiring
- Database'da admin flag'ni tekshiring

### ❌ Valyuta kursi yangilanmaydi
**Sabab:** Database connection yoki migration bajarilmagan

**Yechim:**
```bash
docker-compose exec postgres psql -U expenses_user -d expenses_bot
# SQL ichida:
SELECT * FROM exchange_rates;
# Agar jadval bo'lmasa:
\i /migrations/001_add_exchange_rate_and_admin.sql
```

## 8. Best Practices

1. **Minimal admin'lar** - Faqat kerakli odamlarga admin huquqi bering
2. **Log monitoring** - Admin harakatlarini kuzatib boring
3. **Backup** - Database'ni muntazam backup oling
4. **2FA** (kelajakda) - Telegram 2FA'ni yoqing
5. **Audit trail** - Kim qachon nima qilganini log qiling

## 9. Yangi funksiyalar qo'shish (developers uchun)

### Yangi admin endpoint qo'shish:

```python
# api/routers/admin.py
@router.post("/admin/new-feature")
async def new_admin_feature(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await verify_admin(current_user, db)
    
    # Your admin logic here
    
    return {"success": True}
```

### Mini App'ga yangi admin sahifa qo'shish:

```typescript
// miniapp/src/components/AdminNewFeature.tsx
export const AdminNewFeature: React.FC = () => {
  // Your component logic
}

// App.tsx'ga route qo'shish:
<Route path="/admin/new-feature" element={<AdminNewFeature />} />
```

## 10. Monitoring va Analytics

### Admin harakatlarini kuzatish:

```sql
-- Exchange rate o'zgarishlarini ko'rish
SELECT 
  er.from_currency,
  er.to_currency,
  er.rate,
  u.username as updated_by,
  er.updated_at
FROM exchange_rates er
LEFT JOIN users u ON er.updated_by = u.id
ORDER BY er.updated_at DESC;

-- Eng faol adminlarni ko'rish
SELECT 
  u.id,
  u.username,
  u.first_name,
  COUNT(*) as actions_count
FROM users u
JOIN exchange_rates er ON er.updated_by = u.id
WHERE u.is_admin = true
GROUP BY u.id
ORDER BY actions_count DESC;
```

---

## Qo'shimcha yordam

Agar qo'shimcha yordam kerak bo'lsa:
1. Log'larni tekshiring: `docker-compose logs -f`
2. Database'ni tekshiring: `docker-compose exec postgres psql -U expenses_user expenses_bot`
3. API docs'ga qaring: `http://localhost:8000/docs`

**Admin Panel'dan bahramand bo'ling! 🎉**
