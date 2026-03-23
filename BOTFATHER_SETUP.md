# BotFather sozlamalari / BotFather Configuration

## 1. Botni yaratish / Creating the bot

Agar hali botingiz yo'q bo'lsa:

1. Telegramda [@BotFather](https://t.me/botfather) ni oching
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: "My Expenses Bot")
4. Bot username'ini kiriting (masalan: "my_expenses_bot")
5. Tokenni oling va `.env` fayliga qo'ying

## 2. Bot commands sozlash / Setting up bot commands

BotFather'da botingizni tanlang va quyidagi buyruqlarni qo'shing:

### `/setcommands` buyrug'i uchun:

**O'zbek tili uchun (uz):**
```
start - Botni ishga tushirish
help - Yordam
income - Daromad qo'shish
expense - Xarajat qo'shish
balance - Balansni ko'rish
stats - Statistika
transfer - Pul o'tkazish
transfers - Mening o'tkazmalarim
received - Qabul qilingan o'tkazmalar
settings - Sozlamalar
currency - Valyutani o'zgartirish
language - Tilni o'zgartirish
report - Hisobot yaratish
cancel - Bekor qilish
menu - Asosiy menyu
```

**Rus tili uchun (ru):**
```
start - Запустить бота
help - Помощь
income - Добавить доход
expense - Добавить расход
balance - Показать баланс
stats - Статистика
transfer - Перевести деньги
transfers - Мои переводы
received - Полученные переводы
settings - Настройки
currency - Изменить валюту
language - Изменить язык
report - Создать отчёт
cancel - Отмена
menu - Главное меню
```

**Ingliz tili uchun (en):**
```
start - Start the bot
help - Help
income - Add income
expense - Add expense
balance - Show balance
stats - Statistics
transfer - Transfer money
transfers - My transfers
received - Received transfers
settings - Settings
currency - Change currency
language - Change language
report - Generate report
cancel - Cancel
menu - Main menu
```

### BotFather'da amalga oshirish:

1. BotFather'da botingizni tanlang
2. `/setcommands` ni yuboring
3. Yuqoridagi ro'yxatni nusxalang va yuboring (har bir til uchun)
4. Har bir til uchun `/setlanguage` dan foydalaning:
   - `/setlanguage` -> `uz` -> yuqoridagi o'zbek buyruqlarini kiriting
   - `/setlanguage` -> `ru` -> yuqoridagi rus buyruqlarini kiriting
   - `/setlanguage` -> `en` -> yuqoridagi ingliz buyruqlarini kiriting

## 3. Bot tavsifini sozlash / Setting bot description

### `/setdescription` - Bot tavsifi:

**O'zbek tili:**
```
Moliyaviy harajatlar va daromadlarni boshqarish boti. 

✅ Daromad va xarajatlarni kuzating
✅ Boshqalarga pul o'tkazing va ularning xarajatlarini nazorat qiling
✅ Batafsil statistika va hisobotlar
✅ 3 til: O'zbek, Rus, Ingliz
✅ 2 valyuta: UZS va USD
```

**Rus tili:**
```
Бот для управления финансами, доходами и расходами.

✅ Отслеживайте доходы и расходы
✅ Переводите деньги другим и контролируйте их траты
✅ Подробная статистика и отчёты
✅ 3 языка: Узбекский, Русский, Английский
✅ 2 валюты: UZS и USD
```

**Ingliz tili:**
```
Financial management bot for tracking income and expenses.

✅ Track income and expenses
✅ Transfer money to others and monitor their spending
✅ Detailed statistics and reports
✅ 3 languages: Uzbek, Russian, English
✅ 2 currencies: UZS and USD
```

### `/setabouttext` - Qisqa tavsif:

**O'zbek:**
```
Moliyaviy harajatlar va daromadlarni boshqarish boti
```

**Rus:**
```
Бот для управления финансами и расходами
```

**Ingliz:**
```
Financial management and expense tracking bot
```

## 4. Mini App sozlash / Setting up Mini App

Mini App ni ulash uchun:

### 4.1. Frontend (miniapp) ni ishga tushiring:

```bash
cd miniapp
npm install
npm run dev
```

Bu sizning frontend'ingizni local'da ishga tushiradi (masalan: `http://localhost:5173`)

### 4.2. ngrok yoki localtunnel bilan tunnel oching:

**ngrok bilan:**
```bash
ngrok http 5173
```

Natija:
```
Forwarding: https://abc123.ngrok-free.app -> http://localhost:5173
```

**localtunnel bilan:**
```bash
npx localtunnel --port 5173
```

### 4.3. Menu button uchun URL sozlash:

1. BotFather'da `/setmenubutton` ni yuboring
2. Botingizni tanlang
3. Mini App URL'ni kiriting (masalan: `https://abc123.ngrok-free.app`)
4. Button nomini kiriting (masalan: "📱 Open App")

### 4.4. `.env` faylda Mini App URL ni yangilang:

```env
MINIAPP_URL=https://abc123.ngrok-free.app
```

## 5. Bot sozlamalarini tekshirish / Verify bot settings

BotFather'da:
- `/mybots` - botingizni tanlang
- `Bot Settings` -> `Menu Button` - Mini App URL'ni tekshiring
- `Edit Commands` - barcha buyruqlar to'g'ri o'rnatilganini tekshiring

## 6. Botni test qilish / Testing the bot

### 6.1. Polling mode bilan (test uchun eng oson):

```bash
cd c:\Users\Xolmirza\Desktop\expenses-bot
.\env\Scripts\Activate.ps1
python run_bot_dev.py
```

Bu webhook kerak bo'lmasdan botni ishga tushiradi.

### 6.2. Webhook mode bilan (production uchun):

Webhook uchun sizga:
1. Public HTTPS URL kerak (masalan ngrok)
2. Backend API ni ishga tushirish kerak

```bash
# Terminal 1 - Backend API
python api_server.py

# Terminal 2 - ngrok
ngrok http 8000

# .env faylda webhook URL'ni yangilang:
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook
USE_WEBHOOK=true

# Bot'ni ishga tushiring
python main.py
```

## 7. Admin qilish / Making yourself admin

Database'da o'zingizni admin qiling:

```sql
-- Your Telegram ID ni bilish uchun botga /start yuboring va log'larni qarang
UPDATE users SET is_admin = true WHERE id = YOUR_TELEGRAM_ID;
```

Yoki Python script orqali:

```python
from database.session import get_db
from database.models import User
from sqlalchemy import update

async def make_admin(user_id: int):
    async with get_db() as db:
        await db.execute(
            update(User).where(User.id == user_id).values(is_admin=True)
        )
        await db.commit()

# Ishlatish:
# await make_admin(YOUR_TELEGRAM_ID)
```

## 8. Muhim eslatmalar / Important notes

1. **Test uchun:** Polling mode ishlatish tavsiya etiladi (`run_bot_dev.py`)
2. **Mini App uchun:** ngrok yoki localtunnel kerak bo'ladi
3. **Production uchun:** Haqiqiy domen va SSL sertifikat kerak
4. **Database:** Botni ishga tushirishdan oldin migration'larni bajaring
5. **Token:** `.env` fayldagi tokenni hech qachon share qilmang!

## 9. Umumiy muammolar va yechimlar / Common issues

### Mini App ochilmaydi:
- ngrok/localtunnel ishlab turganini tekshiring
- URL to'g'ri kiritilganini tekshiring (HTTPS bo'lishi kerak)
- BotFather'da menu button to'g'ri sozlanganini tekshiring

### Bot javob bermaydi:
- Token to'g'ri kiritilganligini tekshiring
- Bot ishlab turganini tekshiring
- Internet aloqasini tekshiring

### Database xatolari:
- PostgreSQL ishlab turganini tekshiring
- Migration'lar bajarilganini tekshiring
- Database connection string to'g'ri ekanligini tekshiring

## 10. Qo'shimcha sozlamalar / Additional settings

### Bot rasmi o'rnatish:
1. BotFather'da `/setuserpic`
2. Rasm yuklang (512x512 px tavsiya etiladi)

### Bot privacy sozlash:
1. `/setprivacy` - Guruhlar uchun ruxsat
2. `/setjoingroups` - Guruhga qo'shish imkoniyati

### Inline mode (ixtiyoriy):
1. `/setinline` - Inline mode yoqish
2. `/setinlinefeedback` - Feedback yoqish
