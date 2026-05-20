# Pracharuk Medic Bot

Discord bot สำหรับเซิร์ฟเวอร์ Role-Play (RP) ของโรงพยาบาล Pracharuk
ใช้สร้างใบนัด/ใบรับรองแพทย์, ออกบัตรประกัน, บันทึกชั่วโมงเวร (OT) และประวัติศัลยกรรมลง MongoDB

---

## 🚀 Deploy บน Railway

โปรเจกต์นี้ออกแบบให้รันบน **Railway** (worker process — ไม่ใช่ web server)

### 1. Push โค้ดขึ้น GitHub

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### 2. สร้างโปรเจกต์บน Railway

1. ไปที่ [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. เลือก repo `pracharuk-medic-bot`
3. Railway จะอ่าน `nixpacks.toml` / `railway.json` / `Procfile` อัตโนมัติ

### 3. Environment Variables

ตั้งใน Railway → **Variables** ตามรายการนี้ (มีอยู่แล้ว ไม่ต้องเปลี่ยน)

| ตัวแปร | คำอธิบาย |
|---|---|
| `DISCORD_TOKEN` | Bot token จาก Discord Developer Portal |
| `MONGO_URL` | MongoDB connection string |
| `DELETE_CODE` | รหัสผ่านสำหรับคำสั่ง `/ลบข้อความ` |
| `OT_ADMIN_PASSWORD` | รหัสผ่านสำหรับดู OT รวมทุกคน |
| `SOURCE_CHANNEL_ID` | Channel ID ที่ webhook ส่ง On/Off Duty |
| `CONFIRM_CHANNEL_ID` | Channel ID สำหรับ confirm เวลาทำงาน > 8 ชม. |
| `SURGERY_CHANNEL_ID` | Channel ID ที่บันทึกประวัติศัลยกรรม |

> Railway จะตั้ง `RAILWAY_ENVIRONMENT` ให้อัตโนมัติ บอทจะข้าม `load_dotenv()` เอง

### 4. Deploy

Railway จะ build และ start บอททันที — ดู log ที่แท็บ **Deployments**

---

## 🗂️ โครงสร้างโปรเจกต์

```
pracharuk-medic-bot/
├── bot.py                    # Entry point — โหลด command + start bot
├── requirements.txt
├── Procfile / nixpacks.toml / railway.json   # Config สำหรับ Railway
├── .env.example
├── assets/
│   ├── template.jpg          # บัตรประกัน 7 วัน (ตัวอักษรดำ)
│   ├── template_2.jpg        # บัตรประกัน 1 เดือน (ตัวอักษรขาว)
│   └── Kanit-Regular.ttf     # ฟอนต์ไทย
├── commands/                 # Slash commands ทั้งหมด
│   ├── admit_command.py      # /เคสพิเศษ
│   ├── cancer_command.py     # /มะเร็ง
│   ├── delete_command.py     # /ลบข้อความ (admin)
│   ├── dna_command.py        # /แมชdna, /ตรวจdna
│   ├── drug_command.py       # /ยาเสพติด
│   ├── help_command.py       # /คำสั่ง
│   ├── insurance_command.py  # /ออกบัตรประกัน
│   ├── off_duty_command.py   # /offduty
│   ├── ot_command.py         # /ot
│   ├── splint_command.py     # /เฝือก
│   ├── surgery_command.py    # /ศัลยกรรม
│   └── vaccine_command.py    # /วัคซีน
└── handlers/                 # on_message handlers
    ├── duty_handler.py       # คำนวณชั่วโมงทำงานจาก On/Off Duty
    └── surgery_handler.py    # บันทึกประวัติศัลยกรรม
```

---

## 📋 รายการคำสั่ง

| Slash Command | ใช้ทำอะไร | บันทึก DB |
|---|---|---|
| `/คำสั่ง` | แสดงรายการคำสั่งทั้งหมด | — |
| `/เคสพิเศษ` | รายงานผู้ป่วยบาดเจ็บสาหัส (แนบรูป + Modal) | — |
| `/ยาเสพติด` | ใบนัดบำบัดผู้ติดสารเสพติด | — |
| `/เฝือก` | ใบนัดใส่/ถอดเฝือก | — |
| `/มะเร็ง` | ใบนัดผู้ป่วยมะเร็ง (Modal 2 ขั้นตอน) | — |
| `/แมชdna` | ใบรับรอง Match DNA (Modal 2 ขั้นตอน) | — |
| `/ตรวจdna` | ใบรับรองตรวจ DNA อาชญากรรม (Modal 2 ขั้นตอน) | — |
| `/ออกบัตรประกัน` | สร้างบัตร Pracharuk Care (รูปบัตร PNG) | — |
| `/วัคซีน` | ระบบฉีดวัคซีนพิษสุนัขบ้า 5 เข็ม (กดปุ่มสะสมเข็ม) | — |
| `/offduty` | แจ้ง Off Duty นอกเมือง | trigger duty_handler |
| `/ot` | ดูสรุป OT รายคน / ทุกคน (มีรหัสผ่าน) | อ่าน `Shift_Time` |
| `/ศัลยกรรม` | ดูประวัติศัลยกรรมของผู้ใช้บริการ | อ่าน `Surgery` |
| `/ลบข้อความ` | ลบ Embed บอท (มีรหัสผ่าน + DM backup) | — |
| `/reload` | sync คำสั่ง (owner only) | — |
| `/restart` | restart บอท (owner only) | — |

---

## 🗄️ MongoDB Schema

**Database:** `pracharuk_medic`

### Collection `Shift_Time`
```json
{
  "ชื่อ": "Prime McFly",
  "วันที่": "29-08-2025",
  "ชั่วโมง": 6.5
}
```

### Collection `Surgery`
```json
{
  "ชื่อแพทย์": "Dr. Foo",
  "ชื่อผู้ใช้บริการ": "Prime McFly",
  "วันที่ศัลยกรรม": "29.08.2025",
  "เวลาที่ศัลยกรรม": "13:45:30"
}
```

---

## 🔄 Logic การคำนวณเวลาเวร

ทำงานใน `handlers/duty_handler.py` — trigger จาก webhook embed ที่มี:
- **title** = ชื่อพนักงาน
- **description** = `On duty` หรือ `Off duty`
- **footer** = `เวลา : DD.MM.YYYY - HH:MM:SS`

เมื่อบอทเห็น Embed `Off duty`:
1. ค้น 100 ข้อความก่อนหน้าหา `On duty` ของชื่อเดียวกัน
2. ถ้าเจอ → คำนวณช่วงเวลา (ชั่วโมง)
3. **ถ้า ≤ 8 ชม.** → insert MongoDB เลย
4. **ถ้า > 8 ชม.** → ส่งการ์ดยืนยันไป `CONFIRM_CHANNEL_ID` ให้แอดมินกดยืนยัน
5. ถ้าเจอ `Off duty` ก่อน → ไม่คำนวณ

## 💉 Logic การฉีดวัคซีนพิษสุนัขบ้า

ทำงานใน `commands/vaccine_command.py` — **stateless** (อ่าน state จาก Embed)

**Flow:**
1. `/วัคซีน` + แนบรูป → ส่ง View ephemeral 2 ปุ่ม (พิษสุนัขบ้า / บาดทะยัก)
2. กด "วัคซีนพิษสุนัขบ้า" → เปิด Modal (ชื่อ-สกุล + Select กรุ๊ปเลือด + Select เพศ)
3. Submit → ส่ง 2 ข้อความใน channel:
   - **Embed รายงานผู้ป่วย** (มีรูป thumbnail + ฟิลด์สถานะเข็ม ⬜⬜⬜⬜⬜)
   - **ข้อความปุ่มควบคุม** ที่ reply กลับ Embed ข้างต้น พร้อมปุ่ม "ฉีดเข็มที่ N" + "เริ่มใหม่"

**กดปุ่ม "ฉีดเข็ม":**
- Fetch ข้อความที่ reply ถึง → อ่าน state จาก Embed (นับ ✅)
- อัปเดต Embed: เปลี่ยน ⬜ เป็น ✅ + คำนวณวันที่นัดถัดไป (เป็นภาษาไทย พ.ศ.)
- เปลี่ยน label ปุ่มเป็น "ฉีดเข็มที่ N+1"
- เข็ม 5 → ปุ่ม disabled + title มี `5️⃣✅`

**ระยะนัด:**

| ฉีดเข็ม | นัดเข็มถัดไป |
|---|---|
| 1 → 2 | +3 วัน |
| 2 → 3 | +7 วัน |
| 3 → 4 | +14 วัน |
| 4 → 5 | +30 วัน |

**ปุ่ม persistent:** ใช้ `custom_id` คงที่ + `bot.add_view()` ใน `on_ready` → ปุ่มใช้ได้ตลอดแม้บอท restart, **ไม่หมดเวลา**

---

## 🩺 Logic การบันทึกศัลยกรรม

ทำงานใน `handlers/surgery_handler.py` — ใน `SURGERY_CHANNEL_ID` เท่านั้น
- รอ Embed description = `ทำการศัลยกรรม`
- ค้น 20 ข้อความก่อนหน้าหา Embed description = `ใช้บัตรศัลยกรรม`
- ถ้าเจอ → บันทึก {ชื่อแพทย์, ชื่อผู้ใช้บริการ, วันที่, เวลา}

---

## ⚠️ Known Issues / TODO

- `datetime.utcnow()` ถูก deprecate ใน Python 3.12+ ควรเปลี่ยนเป็น `datetime.now(timezone.utc)` (ยังใช้ได้แต่จะมี warning)
- `commands/cancer_command.py` มีโค้ดที่ `now_thai` คำนวณ timezone ค่อนข้างซับซ้อนเกินจำเป็น
- `MONGO_URL.split(':')[2]` ใน `ot_command.py` จะ crash ถ้า URL ไม่มี password (เช่น mongodb://localhost)
