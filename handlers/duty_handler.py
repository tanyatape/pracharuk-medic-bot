import discord
from datetime import datetime
import os

# ✅ แปลงค่า env เป็น int (กันปัญหา string != int)
try:
    SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", 0))
    TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", 0))
except ValueError:
    print("❌ SOURCE_CHANNEL_ID หรือ TARGET_CHANNEL_ID ไม่ใช่ตัวเลข")
    SOURCE_CHANNEL_ID = 0
    TARGET_CHANNEL_ID = 0


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


async def handle_on_message(message: discord.Message, bot: discord.Client):
    print(f"\n📩 [DEBUG] New message by {message.author} in channel {message.channel.id}")
    print(f"[DEBUG] Message webhook_id: {message.webhook_id}")

    if message.channel.id != SOURCE_CHANNEL_ID:
        print(f"[DEBUG] Message is from channel {message.channel.id}, not SOURCE_CHANNEL_ID {SOURCE_CHANNEL_ID}")
        return

    if not message.embeds:
        print("[DEBUG] Message has no embeds.")
        return

    embed = message.embeds[0]
    title = embed.title
    description = embed.description
    footer_text = embed.footer.text if embed.footer else None

    print(f"[DEBUG] Embed info:\n  - Title: {title}\n  - Description: {description}\n  - Footer: {footer_text}")

    if not all([title, description, footer_text]):
        print("[DEBUG] Embed missing title, description, or footer.")
        return

    if description.lower().strip() != "off duty":
        print(f"[DEBUG] Description is not 'Off Duty' → '{description}'")
        return

    off_time = parse_footer_time(footer_text)
    if not off_time:
        print("[DEBUG] Failed to parse Off Duty time.")
        return

    print("[DEBUG] 🔍 Checking previous messages for Off/On Duty validation...")

    async for msg in message.channel.history(limit=100):
        if msg.id == message.id or not msg.embeds:
            continue

        prev_embed = msg.embeds[0]
        prev_title = prev_embed.title
        prev_description = prev_embed.description
        prev_footer = prev_embed.footer.text if prev_embed.footer else None

        if prev_title != title or not prev_description or not prev_footer:
            continue

        desc_lower = prev_description.lower().strip()

        print(f"[DEBUG] Checking message:\n  - Title: {prev_title}\n  - Desc: {desc_lower}\n  - Footer: {prev_footer}")

        # ❌ ถ้าเจอ Off Duty ก่อนหน้า → หยุด ไม่คำนวณ
        if desc_lower == "off duty":
            print("❌ พบ Off Duty ก่อนหน้า → ไม่คำนวณ")
            print(f"⚠️ ไม่สามารถคำนวณเวลาให้ {title} ได้ เพราะพบ Off Duty ก่อนหน้า โดยไม่มี On Duty")
            return

        # ✅ เจอ On Duty → คำนวณเวลา
        if desc_lower == "on duty":
            on_time = parse_footer_time(prev_footer)
            if not on_time:
                print("[DEBUG] Failed to parse On Duty time.")
                return

            duration = off_time - on_time
            hours = duration.total_seconds() / 3600
            print(f"[✅] คำนวณเวลา On -> Off ได้ {hours:.2f} ชั่วโมง")

            result_embed = discord.Embed(
                title=title,
                description=f"เวลาการทำงาน {hours:.2f} ชั่วโมง",
                color=discord.Color.blue()
            )
            result_embed.set_footer(text="ตรวจสอบโดย Pracharuk Medic")
            result_embed.timestamp = datetime.utcnow()

            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                await target_channel.send(embed=result_embed)
                print("[✅] ส่งข้อความคำนวณเวลาไปยัง Target Channel แล้ว")
            else:
                print(f"❌ ไม่พบ Target Channel: {TARGET_CHANNEL_ID}")
            return

    # ⚠️ ไม่เจอทั้ง Off Duty หรือ On Duty ก่อนหน้า
    print(f"⚠️ ไม่พบข้อความ 'On Duty' ล่าสุดสำหรับ {title}")
