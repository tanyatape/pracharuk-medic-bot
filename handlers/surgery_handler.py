import discord
from datetime import datetime
import os
from pymongo import MongoClient

# อ่าน env
try:
    SURGERY_CHANNEL_ID = int(os.getenv("SURGERY_CHANNEL_ID", 0))
    MONGO_URI = os.getenv("MONGO_URL")
except ValueError:
    print("❌ SURGERY_CHANNEL_ID ไม่ใช่ตัวเลข")
    SURGERY_CHANNEL_ID = 0
    MONGO_URI = None

# DB config
DB_NAME = "pracharuk_medic"
COLLECTION_NAME = "Surgery"

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

def parse_footer_time(footer_text):
    try:
        prefix = "เวลา : "
        if not footer_text.startswith(prefix):
            print(f"[DEBUG] footer_text '{footer_text}' ไม่ได้ขึ้นต้นด้วย '{prefix}'")
            return None

        time_str = footer_text.replace(prefix, "")
        parsed_time = datetime.strptime(time_str, "%d.%m.%Y - %H:%M:%S")
        print(f"[DEBUG] Parsed footer time: {parsed_time}")
        return parsed_time
    except Exception as e:
        print(f"❌ Failed to parse time from footer '{footer_text}': {e}")
        return None

async def handle_surgery_message(message: discord.Message, bot: discord.Client):
    print(f"\n📩 [DEBUG] New message in surgery channel {message.channel.id}")

    if message.channel.id != SURGERY_CHANNEL_ID:
        print(f"[DEBUG] Message is not from surgery channel {SURGERY_CHANNEL_ID}")
        return

    if not message.embeds:
        print("[DEBUG] Message has no embeds.")
        return

    embed = message.embeds[0]
    title = embed.title
    description = embed.description
    footer_text = embed.footer.text if embed.footer else None

    print(f"[DEBUG] Embed:\n  - Title: {title}\n  - Description: {description}\n  - Footer: {footer_text}")

    if not all([title, description, footer_text]):
        print("[DEBUG] Embed missing title, description, or footer.")
        return

    description = description.strip()

    if description == "ใช้บัตรศัลยกรรม":
        print("[DEBUG] ข้ามข้อความ 'ใช้บัตรศัลยกรรม'")
        return

    if description != "ทำการศัลยกรรม":
        print(f"[DEBUG] ข้ามข้อความคำอธิบายไม่ตรง → '{description}'")
        return

    surgery_time = parse_footer_time(footer_text)
    if not surgery_time:
        print("[DEBUG] ไม่สามารถแปลง footer เป็นเวลาได้")
        return

    print("[DEBUG] 🔍 กำลังค้นหาข้อความก่อนหน้า 'ใช้บัตรศัลยกรรม'")

    async for prev_msg in message.channel.history(limit=20, before=message.created_at):
        if not prev_msg.embeds:
            continue

        prev_embed = prev_msg.embeds[0]
        prev_title = prev_embed.title
        prev_description = prev_embed.description

        if not prev_title or not prev_description:
            continue

        if prev_description.strip() == "ใช้บัตรศัลยกรรม":
            data = {
                "ชื่อแพทย์": prev_title,
                "ชื่อผู้ใช้บริการ": title,
                "วันที่ศัลยกรรม": surgery_time.strftime("%d.%m.%Y"),
                "เวลาที่ศัลยกรรม": surgery_time.strftime("%H:%M:%S")
            }

            collection.insert_one(data)
            print(f"[✅] บันทึกข้อมูลการศัลยกรรม: {data}")
            return

    print("[⚠️] ไม่พบข้อความ 'ใช้บัตรศัลยกรรม' ก่อนหน้า")
