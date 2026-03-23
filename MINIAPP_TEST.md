# Mini App Test Qilish Yo'riqnomasi

## 1. Local Test (Kompyuterda test qilish)

### A. Telegram Desktop orqali test qilish

#### 1-qadam: Mini app ni ishga tushirish
```powershell
# Loyihaning miniapp papkasiga kirish
cd miniapp

# Dependencies o'rnatish (birinchi marta)
npm install

# Development server ishga tushirish
npm run dev
```

Bu sizning kompyuteringizda `http://localhost:5173` da mini app ishga tushadi.

#### 2-qadam: Telegram Desktop ni sozlash

1. **Telegram Desktop** ni oching
2. **Settings** → **Advanced** → **Experimental settings**
3. **"Enable webview inspection"** ni yoqing

#### 3-qadam: Bot orqali mini app ni ochish

Mini app ni bot ichida test qilish uchun:

**Variant A: Ngrok yordamida (Tavsiya etiladi)**

```powershell
# Ngrok o'rnatish (agar yo'q bo'lsa)
# https://ngrok.com/download dan yuklab oling

# Ngrok orqali local serverni ochish
ngrok http 5173
```

Ngrok sizga `https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app` kabi URL beradi.

**Variant B: Serveo yordamida (Bepul)**

```bash
ssh -R 80:localhost:5173 serveo.net
```

#### 4-qadam: Bot sozlamalarini yangilash

`.env` faylida:
```env
# Ngrok URL ni qo'ying
MINIAPP_URL=https://your-ngrok-url.ngrok-free.app
```

#### 5-qadam: Bot ni qayta ishga tushirish

```powershell
# Botni to'xtatib (Ctrl+C), qayta ishga tushiring
python main.py
```

---

## 2. Production Test (Real server da test)

### A. Mini App ni deploy qilish

#### Variant 1: Vercel (Bepul va Oson)

1. **GitHub repositoriyasini yaratish**
   - Loyihani GitHub ga yuklab qo'ying

2. **Vercel ga kirish**
   - https://vercel.com ga kiring
   - GitHub bilan connect qiling

3. **Mini app ni deploy qilish**
   - "Import Project" tugmasini bosing
   - GitHub reponi tanlang
   - `miniapp` papkasini root directory sifatida belgilang
   - Deploy tugmasini bosing

4. **URL olish**
   - Vercel sizga `https://your-app.vercel.app` kabi URL beradi

#### Variant 2: Netlify (Bepul)

1. **Netlify ga kirish**
   - https://netlify.com ga kiring

2. **Deploy qilish**
   ```powershell
   # Netlify CLI o'rnatish
   npm install -g netlify-cli
   
   # Netlify ga login qilish
   netlify login
   
   # miniapp papkasida
   cd miniapp
   npm run build
   
   # Deploy qilish
   netlify deploy --prod
   ```

#### Variant 3: O'z serveringizda (VPS)

```bash
# Server da
cd /var/www/expenses-bot/miniapp

# Dependencies o'rnatish
npm install

# Build qilish
npm run build

# Nginx orqali serve qilish
# Nginx config: /etc/nginx/sites-available/miniapp
```

Nginx config:
```nginx
server {
    listen 80;
    server_name miniapp.yourdomain.com;
    
    root /var/www/expenses-bot/miniapp/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### B. Bot sozlamalarini yangilash

Production `.env` da:
```env
MINIAPP_URL=https://your-production-url.vercel.app
```

---

## 3. BotFather da Mini App sozlash

### Variant A: Web App URL (Tavsiya etiladi)

1. @BotFather ga yozing
2. `/setmenubutton` ni yuboring
3. Botingizni tanlang
4. Mini app URL ni kiriting: `https://your-app.vercel.app`
5. Button nomi: "📱 Open App" yoki "Ochish"

### Variant B: Inline button orqali

Bot kodida (main menu keyboard):
```python
from aiogram.types import KeyboardButton, WebAppInfo

button = KeyboardButton(
    text="📱 Open Mini App",
    web_app=WebAppInfo(url="https://your-app.vercel.app")
)
```

---

## 4. Mini App Test Qilish Checklist

### Development muhitda:

- [ ] `npm run dev` ishlayapti
- [ ] `http://localhost:5173` ochilmoqda
- [ ] Ngrok/Serveo orqali HTTPS URL olindi
- [ ] Bot `.env` da `MINIAPP_URL` to'g'ri sozlangan
- [ ] Bot qayta ishga tushirildi
- [ ] Telegram Desktop da bot ochildi
- [ ] Mini App tugmasi ko'rinmoqda
- [ ] Mini App ochilmoqda va ishlayapti

### Production muhitda:

- [ ] Mini app build qilindi (`npm run build`)
- [ ] Hosting service ga deploy qilindi
- [ ] HTTPS URL olindi
- [ ] SSL sertifikat ishlayapti
- [ ] Bot `.env` yangilandi
- [ ] Bot server qayta ishga tushirildi
- [ ] Telegram (mobile + desktop) da test qilindi
- [ ] Barcha funksiyalar ishlayapti

---

## 5. Debug va Troubleshooting

### Mini App ochilmasa:

1. **Browser Console ni tekshirish**
   - Telegram Desktop: `Ctrl + Shift + I` (Windows/Linux)
   - Chrome DevTools: `F12`

2. **CORS xatolarini hal qilish**
   
   `vite.config.ts` da:
   ```typescript
   export default defineConfig({
     server: {
       cors: true,
       headers: {
         "Access-Control-Allow-Origin": "*"
       }
     }
   })
   ```

3. **Telegram Web App SDK tekshirish**
   
   Browser console da:
   ```javascript
   console.log(window.Telegram.WebApp);
   ```

### Mini App ma'lumotlarni olmasa:

1. **API URL tekshirish**
   
   `miniapp/src/api/client.ts` da:
   ```typescript
   const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
   ```

2. **Telegram auth tekshirish**
   
   Browser console:
   ```javascript
   console.log(window.Telegram.WebApp.initData);
   ```

3. **Backend API ishlayotganini tekshirish**
   ```powershell
   # Terminal da
   curl http://localhost:8000/api/health
   ```

---

## 6. Test Foydalanuvchi Ssenariysi

### Oddiy test:

1. ✅ Bot `/start` komandasi
2. ✅ "📱 Open Mini App" tugmasini bosish
3. ✅ Dashboard ko'rinishi
4. ✅ Income qo'shish
5. ✅ Expense qo'shish
6. ✅ Statistics ko'rish
7. ✅ Settings ochish

### Kengaytirilgan test:

1. ✅ Bir nechta transactions qo'shish
2. ✅ Filterlash funksiyasi
3. ✅ Date picker
4. ✅ Currency switcher
5. ✅ Language switcher
6. ✅ Transfer qilish
7. ✅ Transfer history
8. ✅ Admin panel (admin foydalanuvchi uchun)

---

## 7. Production ga o'tish

### Tayyor bo'lganingizda:

1. **Environment variables sozlash**
   ```env
   # Production .env
   TELEGRAM_BOT_TOKEN=your_production_bot_token
   MINIAPP_URL=https://your-production-miniapp.vercel.app
   API_URL=https://your-api.yourdomain.com
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

2. **Security sozlamalari**
   - HTTPS majburiy
   - CORS sozlamalari
   - Rate limiting
   - API authentication

3. **Monitoring sozlash**
   - Error logging (Sentry)
   - Analytics (Google Analytics)
   - Uptime monitoring

---

## Qo'shimcha Resurslar

- **Telegram Mini Apps Docs**: https://core.telegram.org/bots/webapps
- **Vite Documentation**: https://vitejs.dev
- **React Documentation**: https://react.dev

---

## Savol-Javoblar

**Q: Mini app local da ishlamayapti?**
A: `npm install` va `npm run dev` ni qayta ishga tushiring. Port 5173 band bo'lsa, `vite.config.ts` da port o'zgartiring.

**Q: Telegram da ochilmayapti?**
A: HTTPS URL kerak. Ngrok yoki boshqa tunneling service ishlatilgan bo'lishi kerak.

**Q: Ma'lumotlar yuklanmayapti?**
A: Backend API ishga tushganini va to'g'ri URL sozlanganini tekshiring.

**Q: Telegram user ma'lumotlari kelmayapti?**
A: Bot orqali ochish kerak, browserda to'g'ridan-to'g'ri ochganda ishlamaydi.

---

**Omad tilayman! Savollaringiz bo'lsa, bemalol so'rang! 🚀**
