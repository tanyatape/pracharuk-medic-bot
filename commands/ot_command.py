import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, button, Button
from datetime import datetime
from pymongo import MongoClient
import os
import logging

# ✅ Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ MONGO DB SETUP + DEBUG
MONGO_URL = os.getenv("MONGO_URL")

try:
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # ทดสอบการเชื่อมต่อ
    db = mongo_client["pracharuk_medic"]
    collection = db["Shift_Time"]
    safe_url = MONGO_URL.replace(MONGO_URL.split(':')[2].split('@')[0], "***")
    logger.info(f"✅ MongoDB เชื่อมต่อสำเร็จ: {safe_url}")
except Exception as e:
    logger.error(f"❌ ไม่สามารถเชื่อมต่อ MongoDB ได้: {e}")
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
            view = ConfirmAllView(interaction.user, start, end)
            await interaction.response.send_message(
                "คุณเลือกดูข้อมูลของ **ทุกคน**\nกดปุ่มด้านล่างเพื่อยืนยันและใส่รหัสผ่าน:",
                view=view,
                ephemeral=True
            )
            return

        query = {
            "ชื่อ": name_val,
            "วันที่": {
                "$gte": start.strftime("%d-%m-%Y"),
                "$lte": end.strftime("%d-%m-%Y")
            }
        }
        results = list(collection.find(query))
        logger.info(f"[{name_val}] - พบ {len(results)} รายการในช่วง {start} ถึง {end}")

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

        query = {
            "วันที่": {
                "$gte": self.start.strftime("%d-%m-%Y"),
                "$lte": self.end.strftime("%d-%m-%Y")
            }
        }
        results = list(collection.find(query))
        logger.info(f"[ALL USERS] - พบ {len(results)} รายการ")

        if not results:
            await interaction.response.send_message("ไม่พบข้อมูลในช่วงเวลาดังกล่าว", ephemeral=True)
            return

        summary = {}
        for entry in results:
            name = entry.get("ชื่อ", "ไม่ระบุ")
            hours = entry.get("ชั่วโมง", 0)
            if name not in summary:
                summary[name] = {"count": 0, "hours": 0}
            summary[name]["count"] += 1
            summary[name]["hours"] += hours

        paginated_view = PaginatedEmbedView(self.requester, summary, self.start, self.end)
        await interaction.response.send_message(embed=paginated_view.get_current_embed(), view=paginated_view, ephemeral=False)
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


class PaginatedEmbedView(View):
    def __init__(self, requester: discord.User, summary: dict, start: datetime, end: datetime):
        super().__init__(timeout=180)
        self.requester = requester
        self.start = start
        self.end = end
        self.items_per_page = 25  # ⚠️ Discord embed limit
        self.summary_items = list(summary.items())
        self.current_page = 0
        self.max_page = (len(self.summary_items) - 1) // self.items_per_page

        self.previous_button = Button(label="⬅️ ก่อนหน้า", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="➡️ ถัดไป", style=discord.ButtonStyle.secondary)
        self.previous_button.callback = self.go_previous
        self.next_button.callback = self.go_next

        self.add_item(self.previous_button)
        self.add_item(self.next_button)

    def get_current_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"รวมชั่วโมงการทำงาน {self.start.strftime('%d/%m/%Y')} - {self.end.strftime('%d/%m/%Y')}",
            color=discord.Color.teal(),
            timestamp=datetime.utcnow()
        )

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.summary_items[start_idx:end_idx]

        for name, data in page_items:
            embed.add_field(
                name=name,
                value=f"เข้าเวร : {data['count']} ครั้ง\nจำนวน : {data['hours']:.2f} ชั่วโมง",
                inline=True
            )

        embed.set_footer(
            text=f"ตรวจสอบโดย - {self.requester.display_name} | หน้า {self.current_page + 1}/{self.max_page + 1}",
            icon_url=self.requester.display_avatar.url
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("❌ ปุ่มนี้ไม่ใช่ของคุณ", ephemeral=True)
            return False
        return True

    async def go_previous(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
        else:
            await interaction.response.defer()

    async def go_next(self, interaction: discord.Interaction):
        if self.current_page < self.max_page:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
        else:
            await interaction.response.defer()


# ✅ คำสั่ง Slash Command
@app_commands.command(name="ot", description="คำนวณ OT รวมจากวันที่กำหนด")
async def ot(interaction: discord.Interaction):
    await interaction.response.send_modal(OTModal())
