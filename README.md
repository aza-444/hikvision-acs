# Hikvision Turniket Nazorat Tizimi (Access Control System Pro)
### iVMS-4200 analogi — Xodimlar kirish-chiqishini nazorat qilish va Telegram Bot integratsiyasi

Ushbu dastur **Hikvision turniketlari**, **MinMoe yuzni tanish terminallari (Face Recognition)**, **barmoq izi skanerlari** va **RFID karta o'quvchi eshik kontrollerlari** bilan to'g'ridan-to'g'ri ishlaydi hamda har bir kirish-chiqishni real-time ravishda **Telegram bot** orqali rahbar yoki mas'ullarga yetkazadi.

---

## 📋 Qilinishi kerak bo'lgan ishlar ro'yxati (Barcha bosqichlar)

### 1-bosqich: Kompyuter va dasturni tayyorlash
- [x] Python 3.10 yoki undan yuqori versiyasini o'rnatish.
- [x] Kerakli kutubxonalarni o'rnatish: `pip install -r requirements.txt`.
- [x] Kompyuterni turniket ulangan lokal tarmoqqa (LAN kabel yoki bir xil Wi-Fi router) ulash.

### 2-bosqich: Telegram Botni sozlash (Kirish-chiqish xabarlari uchun)
1. Telegramda **@BotFather** botini oching.
2. `/newbot` buyrug'ini yuboring va botga nom hamda username bering (masalan: `MeningTurniketimBot`).
3. BotFather sizga bergan **HTTP API Token**ni nusxalab oling (masalan: `7123456789:AAHq_ABCDEF...`).
4. Xabar bormoqchi bo'lgan shaxsiy profilingiz yoki Telegram guruhiga kiring:
   - Agar shaxsiy profilingizga bo'lsa: Botga kirib `/start` bosing va **@userinfobot** orqali o'zingizning **ID** raqamingizni oling (masalan: `123456789`).
   - Agar guruhga bo'lsa: Botni guruhga a'zo qilib **Administrator** huquqini bering, guruh ID raqamini oling (masalan: `-100123456789`).
5. Dasturda **⚙️ Sozlamalar -> ✈️ Telegram Bot** bo'limiga kiring:
   - "Telegram xabarnomalarini yoqish" katakchasini belgilang.
   - **Bot Token** va **Chat ID** ni kiriting.
   - **"📩 Botga sinov xabari yuborish"** tugmasini bosib tekshiring.
   - **"Saqlash"** tugmasini bosing.

### 3-bosqich: Turniketni dasturga ulash
1. Dasturda **⚙️ Sozlamalar -> 🖥️ Qurilmalar** bo'limiga o'ting.
2. **"🔍 Tarmoqdan avtomatik qidirish (SADP)"** tugmasini bosing:
   - Tizim mahalliy tarmoqdagi barcha Hikvision turniketlarini avtomatik aniqlaydi.
   - Topilgan qurilmani tanlab, login (`admin`) va turniket parolini kiritasiz.
3. Agar IP manzil ma'lum bo'lsa, **"➕ Qo'lda qo'shish"** orqali kiritishingiz mumkin:
   - IP manzil: masalan, `192.168.1.100`
   - Port: `80`
4. **"🔗 Ulanishni tekshirish"** tugmasi orqali aloqa borligini tasdiqlang va saqlang.

### 4-bosqich: Xodimlarni kiritish
1. **👥 Xodimlar** bo'limiga kiring.
2. **"➕ Yangi xodim"** tugmasini bosing.
3. Ismi, familiyasi, ID raqami va turniket kartasi raqamini (yoki yuz rasmini) kiriting va saqlang.

### 5-bosqich: Ishlatish va Hisobotlar
1. **📊 Dashboard** oynasida xodimlarning kirib-chiqishi real-time tarzda jonli aks etadi.
2. Har bir o'tish Telegram botga avtomatik yetib boradi.
3. **📈 Hisobotlar** bo'limidan oylik davomat tabelini va kechikkanlarni ko'rib, **Excel (.xlsx)** formatida yuklab olish mumkin.

---

## ❓ Qanday kamchiliklar bor edi va qanday tuzatildi?

Avvalgi oddiy dasturlarda quyidagi kamchiliklar mavjud bo'lar edi, ushbu versiyada ular **to'liq bartaraf etildi**:

1. **Kamchilik:** Turniket harakatini bilish uchun har 5-10 soniyada so'rov yuborilardi (Polling kechikishi).
   * **Tuzatish:** `Hikvision AlertStream` (HTTP Long-connection) texnologiyasi joriy etildi. Xodim karta bosgan yoki yuzini ko'rsatgan **shu soniyaning o'zidayoq (0 sekund kechikishsiz)** xabar dasturga va Telegramga yetib boradi.
2. **Kamchilik:** Turniket IP manzilini qo'lda topib yozish talab qilinardi.
   * **Tuzatish:** Hikvision rasmiy **SADP (Multicast UDP 37020)** va subnet IP skaneri qo'shildi. Endi bitta tugma bilan tarmoqdagi barcha Hikvision qurilmalari avtomatik topiladi.
3. **Kamchilik:** Har xil avlod Hikvision qurilmalarida formatlar mos kelmasdi (ba'zilari faqat XML, ba'zilari JSON yuborardi).
   * **Tuzatish:** Universal gibrid parser qurildi. Turniket qaysi formatda (XML yoki JSON) ma'lumot uzatishidan qat'i nazar, dastur ikkalasini ham avtomatik taniydi.
4. **Kamchilik:** Rahbariyat xodimlar kelganini bilish uchun faqat kompyuterga qarab o'tirishi kerak edi.
   * **Tuzatish:** Telegram Bot integratsiyasi qo'shildi. Xodimlar kirganida yoki chiqqanida (yoki faqat 09:00 dan kech qolganlarida) Telegramga chiroyli xabarnoma boradi.

---

## 🏢 Hamma Hikvision turniketlariga tushadimi?

**Ha!** Dastur Hikvision kompaniyasining xalqaro standarti bo'lgan **ISAPI (Intelligent Server API)** protokoli asosida ishlaydi. Quyidagi barcha qurilmalar bilan 100% mos keladi:
- **Hikvision DS-K3G / DS-K3B seriyali barcha turniketlar** (Tripod, Flap barrier, Swing barrier).
- **Hikvision MinMoe yuzni tanish terminallari** (DS-K1T341, DS-K1T671, DS-K1T343, DS-K1T673 va boshqalar).
- **Hikvision ko'p eshikli kontrollerlari** (DS-K2601, DS-K2602, DS-K2604, DS-K2800 seriya).
- **Hikvision RFID karta o'quvchi terminallari** (DS-K1T804 va boshqalar).

---

## ⚡ Tezkor Ishga Tushirish

```bash
# 1. Loyiha papkasiga kirish
cd hikvision_acs

# 2. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. Dasturni ishga tushirish
python main.py
```

### Jismoniy turniketsiz test qilish:
Agar turniket yo'q bo'lsa yoki Telegram botni sinab ko'rmoqchi bo'lsangiz:
```bash
python simulator.py
```
Bu simulyator har 4 soniyada sun'iy kirish-chiqish hodisalarini hosil qilib, dasturga va Telegram botingizga yuborib turadi.

---

## 📦 Windows uchun `.exe` Fayl Yasash

Python o'rnatilmagan kompyuterlarda dasturni bitta `.exe` fayl sifatida ishlatish uchun:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --add-data "resources:resources" --name "HikvisionACS" main.py
```
*(Windows CMD da `:` o'rniga `;` ishlatiladi: `--add-data "resources;resources"`)*
Tayyor fayl `dist/HikvisionACS/HikvisionACS.exe` manzilida hosil bo'ladi.
