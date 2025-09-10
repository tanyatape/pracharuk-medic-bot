import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, button
from datetime import datetime
from pymongo import MongoClient
import os

# ✅ MONGO DB SETUP + DEBUG
MONGO_URL = os.getenv("MONGO_URL")

try:
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # ทดสอบการเชื่อมต่อ
    db = mongo_client["pracharuk_medic"]
    collection = db["Shift_Time"]
    safe_url = MONGO_URL.replace(MONGO_URL.split(':')[2].split('@')[0], "***")
    print(f"✅ MongoDB เชื่อมต่อสำเร็จ: {safe_url}")
except Exception as e:
    print(f"❌ ไม่สามารถเชื่อมต่อ MongoDB ได้: {e}")
    collection = None


class OTModal(Modal, title="ตรวจสอบชั่วโมงเวร"):
    def __init__(self):
        super().__init__()
        self.name = TextInput(label="ชื่อ (ให้ตรงกับที่บันทึก)", placeholder="เช่น Prime McFly", required=True)
        self.start_date = TextInput(label="วันที่เริ่ม (dd-mm-yyyy)", placeholder="เช่น 01-09-2025", required=True)
        self.end_date = TextInput(label="วันที่สิ้นสุด (dd-mm-yyyy)", placeholder="เช่น 09-09-2025", required=True)

        self.add_item(self.name)
        self.add_item(self.start_date)
        self.add_item(self.end_date)

    async def on_submit(self, interaction: discord.Interaction):
        if collection is None:
            await interaction.response.send_message("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้", ephemeral=True)
            return

        name_val = self.name.value.strip()
        try:
            start = datetime.strptime(self.start_date.value.strip(), "%d-%m-%Y")
            end = datetime.strptime(self.end_date.value.strip(), "%d-%m-%Y")
        except ValueError:
            await interaction.response.send_message("❌ รูปแบบวันที่ไม่ถูกต้อง (ต้องเป็น dd-mm-yyyy)", ephemeral=True)
            return

        if start > end:
            await interaction.response.send_message("❌ วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด", ephemeral=True)
            return

        if name_val.lower() == "all":
            # ถ้า all ให้รอ confirm ด้วยปุ่มและ modal รหัสผ่าน
            view = ConfirmAllView(interaction.user, start, end)
            await interaction.response.send_message(
                "คุณเลือกดูข้อมูลของ **ทุกคน**\nกดปุ่มด้านล่างเพื่อยืนยันและใส่รหัสผ่าน:",
                view=view,
                ephemeral=True
            )
            return

        # ✅ ดึงข้อมูลจาก DB สำหรับชื่อเฉพาะ
        query = {
            "ชื่อ": name_val,
            "วันที่": {
                "$gte": start.strftime("%d-%m-%Y"),
                "$lte": end.strftime("%d-%m-%Y")
            }
        }

        results = list(collection.find(query))

        if not results:
            await interaction.response.send_message("ไม่พบข้อมูลในช่วงเวลาดังกล่าว", ephemeral=True)
            return

        total_hours = sum(entry.get("ชั่วโมง", 0) for entry in results)

        embed = discord.Embed(
            title=f"สรุป OT ของ {name_val}",
            description=f"ตั้งแต่ `{start.strftime('%d-%m-%Y')}` ถึง `{end.strftime('%d-%m-%Y')}`",
            color=discord.Color.teal()
        )
        embed.add_field(name="จำนวนเวร", value=f"{len(results)} ครั้ง", inline=False)
        embed.add_field(name="ชั่วโมงรวม", value=f"{total_hours:.2f} ชั่วโมง", inline=False)
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)


class PasswordModal(Modal, title="กรุณาใส่รหัสผ่านเพื่อยืนยัน"):
    password_input = TextInput(label="รหัสผ่าน", style=discord.TextStyle.short, placeholder="กรุณาใส่รหัสผ่าน", required=True)

    def __init__(self, requester: discord.User, start: datetime, end: datetime, view: View):
        super().__init__()
        self.requester = requester
        self.start = start
        self.end = end
        self.view = view
        self.correct_password = os.getenv("OT_ADMIN_PASSWORD")

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้รหัสผ่านนี้", ephemeral=True)
            return

        if self.password_input.value != self.correct_password:
            await interaction.response.send_message("❌ รหัสผ่านไม่ถูกต้อง", ephemeral=True)
            return

        if collection is None:
            await interaction.response.send_message("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้", ephemeral=True)
            return

        # ✅ รหัสผ่านถูกต้อง → ดึงข้อมูลทั้งหมด
        query = {
            "วันที่": {
                "$gte": self.start.strftime("%d-%m-%Y"),
                "$lte": self.end.strftime("%d-%m-%Y")
            }
        }
        results = list(collection.find(query))

        if not results:
            await interaction.response.send_message("ไม่พบข้อมูลในช่วงเวลาดังกล่าว", ephemeral=True)
            return

        # ✅ รวมข้อมูลตามชื่อ
        summary = {}
        for entry in results:
            name = entry.get("ชื่อ", "ไม่ระบุ")
            hours = entry.get("ชั่วโมง", 0)
            if name not in summary:
                summary[name] = {"count": 0, "hours": 0}
            summary[name]["count"] += 1
            summary[name]["hours"] += hours

        embed = discord.Embed(
            title=f"รวมชั่วโมงการทำงาน {self.start.strftime('%d/%m/%Y')} - {self.end.strftime('%d/%m/%Y')}",
            color=discord.Color.teal(),
            timestamp=datetime.utcnow()
        )

        items = list(summary.items())
        for i in range(0, len(items), 2):
            name1, data1 = items[i]
            value1 = f"เข้าเวร : {data1['count']} ครั้ง\nจำนวน : {data1['hours']:.2f} ชั่วโมง"
            if i + 1 < len(items):
                name2, data2 = items[i + 1]
                value2 = f"เข้าเวร : {data2['count']} ครั้ง\nจำนวน : {data2['hours']:.2f} ชั่วโมง"
                embed.add_field(name=name1, value=value1, inline=True)
                embed.add_field(name=name2, value=value2, inline=True)
            else:
                embed.add_field(name=name1, value=value1, inline=True)

        embed.set_footer(
            text=f"ตรวจสอบโดย - {self.requester.display_name}",
            icon_url="https://cdn.discordapp.com/avatars/1284559774557409342/4e8e1f39efb438c295a49a533b39fce5?size=1024"
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)
        self.view.stop()


class ConfirmAllView(View):
    def __init__(self, requester: discord.User, start: datetime, end: datetime):
        super().__init__(timeout=60)
        self.requester = requester
        self.start = start
        self.end = end

    @button(label="🔐 ยืนยันดูข้อมูลทั้งหมด", style=discord.ButtonStyle.primary)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("❌ ปุ่มนี้ไม่ใช่ของคุณ", ephemeral=True)
            return

        modal = PasswordModal(self.requester, self.start, self.end, self)
        await interaction.response.send_modal(modal)


@app_commands.command(name="ot", description="คำนวณ OT รวมจากวันที่กำหนด")
async def ot(interaction: discord.Interaction):
    await interaction.response.send_modal(OTModal())
