# 🚛 Algo Group — Driver Status Telegram Bot

Google Sheets bilan integratsiya qilingan Telegram bot. Driverlar holatini (GOOD / MONITOR / RED FLAG) kuzatib boradi.

---

## 📁 Fayl strukturasi

```
driver_bot/
├── bot.py            # Asosiy bot
├── setup_sheet.py    # Google Sheets sozlash (bir marta)
├── requirements.txt  # Python kutubxonalari
├── .env.example      # Environment o'zgaruvchilar namunasi
├── .env              # Sizning sozlamalaringiz (git ga qo'shmang!)
├── credentials.json  # Google Service Account (git ga qo'shmang!)
├── Procfile          # Render.com uchun
└── .gitignore
```

---

## ⚙️ O'rnatish qadamlari

### 1. BotFather — Telegram token olish

1. Telegramda [@BotFather](https://t.me/BotFather) ga oching
2. `/newbot` yuboring
3. Bot nomi va username kiriting
4. Olingan **token** ni saqlang (keyinroq `.env` ga qo'yiladi)

---

### 2. Google Cloud Console — API larni yoqish

1. [Google Cloud Console](https://console.cloud.google.com/) ga kiring
2. Yangi project yarating yoki mavjudini tanlang
3. **APIs & Services → Enable APIs** ga o'ting
4. Quyidagilarni qidirib **Enable** qiling:
   - **Google Sheets API**
   - **Google Drive API**

---

### 3. Service Account yaratish va credentials.json olish

1. **APIs & Services → Credentials** ga o'ting
2. **Create Credentials → Service Account** ni tanlang
3. Ismni kiriting, **Create and Continue** bosing, keyin **Done**
4. Yaratilgan Service Account ni bosing
5. **Keys** tab → **Add Key → Create new key → JSON** → **Create**
6. Yuklab olingan faylni `credentials.json` deb nomlab, loyiha papkasiga qo'ying

---

### 4. Google Sheets ni ulash

1. [Google Sheets](https://sheets.google.com) da yangi jadval yarating
2. URL dagi ID ni saqlang:
   `https://docs.google.com/spreadsheets/d/**SHEET_ID_SHU_YER**/edit`
3. Sheets ni `credentials.json` dagi `client_email` bilan **Editor** sifatida share qiling:
   - **Share → Email qo'shish → Editor roli**

---

### 5. .env faylini to'ldirish

```bash
cp .env.example .env
```

`.env` faylini oching va to'ldiring:

```env
BOT_TOKEN=1234567890:ABCDefghIJKLmnopQRSTuvwxyz
SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

---

### 6. Python kutubxonalarini o'rnatish

```bash
pip install -r requirements.txt
```

---

### 7. Google Sheets ni sozlash (bir marta!)

```bash
python setup_sheet.py
```

Bu quyidagilarni bajaradi:
- Sarlavha qatori yozadi: `STATUS | DRIVER NAME | COMPANY NAME | STATUS_KEY | REASON / NOTES | DATE`
- 1-qatorni freeze qiladi
- Ustun kengliklarini belgilaydi
- Header ga ko'k fon beradi
- `STATUS_KEY` ustunini yashiradi

---

### 8. Botni ishga tushirish

```bash
python bot.py
```

Telegramda botingizga `/start` yuboring — tayyor!

---

## 🌐 Render.com ga deploy qilish

### Tayyorgarlik

Loyihani GitHub ga yuklang (`.env` va `credentials.json` `.gitignore` da bo'lgani uchun yuklangmaydi):

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/driver-bot.git
git push -u origin main
```

### Render.com sozlash

1. [render.com](https://render.com) ga kiring → **New → Background Worker**
2. GitHub repositoriyangizni ulang
3. Sozlamalar:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. **Environment Variables** bo'limiga qo'shing:
   - `BOT_TOKEN` = tokeningiz
   - `SHEET_ID` = sheets ID ingiz
5. `credentials.json` ni yuklash uchun:
   - **Environment → Secret Files** → fayl nomi `credentials.json`, ichiga JSON tarkibini joylashtiring

6. **Create Background Worker** bosing — deploy boshlandi!

---

## 🤖 Bot funksionalligi

| Buyruq / Tugma | Tavsif |
|---|---|
| `/start` | Bosh menyuni ochadi |
| ➕ Add Driver | 4 qadam: Company → Ism → Status → Sabab |
| 📋 Driver List | Status bo'yicha driverlar ro'yxati |
| 📊 Stats | Jami statistika va emoji bar chart |

### Status ma'nolari

| Status | Rang | Ma'nosi |
|---|---|---|
| 🟢 GOOD | Yashil | Hamma yaxshi |
| 🟡 MONITOR | Sariq | Kuzatish kerak |
| 🔴 RED FLAG | Qizil + bold | Darhol e'tibor kerak! |

---

## 🔐 Xavfsizlik

- `credentials.json` va `.env` ni **hech qachon** git ga qo'shmang
- `.gitignore` da ikkalasi ham mavjud
- Barcha xatolar `logging` orqali yoziladi

---

## 🛠 Muammolar va yechimlar

**"credentials.json topilmadi" xatosi:**
→ Faylni loyiha papkasiga qo'ying, `python bot.py` ishlatgan papkada bo'lishi kerak

**"SHEET_ID topilmadi" xatosi:**
→ `.env` faylini tekshiring, to'g'ri ID yozilganligini tasdiqlang

**Bot javob bermayapti:**
→ `BOT_TOKEN` to'g'riligini tekshiring, BotFather dan yangisini oling

**Google Sheets ga yozilmayapti:**
→ Service Account emaili jadval bilan Editor sifatida share qilinganligini tekshiring
