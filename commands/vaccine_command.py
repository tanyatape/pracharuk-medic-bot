# commands/vaccine_command.py

import discord
from discord import app_commands, ui
from datetime import datetime, timedelta, timezone
import aiohttp
import io

# ============================================================
# CONSTANTS
# ============================================================

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

DOSE_COUNT = 5

# ระยะเวลานัด (วัน) หลังจากฉีดเข็มที่ N ไปฉีดเข็มที่ N+1
NEXT_DOSE_DAYS = {1: 3, 2: 7, 3: 14, 4: 30}

# Custom IDs สำหรับ persistent view (ห้ามเปลี่ยน — ใช้ resolve view หลัง bot restart)
CUSTOM_ID_INJECT = "vaccine_rabies_inject_v1"
CUSTOM_ID_RESET = "vaccine_rabies_reset_v1"

# Field names ใน Embed (ใช้ทั้งตอนสร้างและ parse กลับ)
FIELD_PATIENT_NAME = "👤 ชื่อคนไข้"
FIELD_BLOOD = "🩸 กรุ๊ปเลือด"
FIELD_GENDER = "🦲 เพศ"
FIELD_STATUS_DOSES = "💉 สถานะวัคซีน"
FIELD_STATUS_TEXT = "📊 STATUS"
FIELD_DOCTOR = "👨‍⚕️ แพทย์ผู้ลงบันทึก"

EMBED_TITLE_BASE = "🏥 ระบบวัคซีนป้องกันพิษสุนัขบ้า"
EMBED_TITLE_DONE = f"{EMBED_TITLE_BASE} 5️⃣✅"


# ============================================================
# HELPERS
# ============================================================

def now_th() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=7)


def thai_date(dt: datetime) -> str:
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"


def build_dose_lines(doses_done: int) -> str:
    lines = []
    for i in range(1, DOSE_COUNT + 1):
        emoji = "✅" if i <= doses_done else "⬜"
        lines.append(f"{emoji} เข็มที่ {i}")
    return " ,\n".join(lines)


def build_status_text(patient_name: str, doses_done: int) -> str:
    if doses_done == 0:
        return "เริ่มต้นการรักษา"
    if doses_done >= DOSE_COUNT:
        return "✅ การรักษาเสร็จสมบูรณ์ (ฉีดครบ 5 เข็ม)"

    next_dose = doses_done + 1
    days_to_next = NEXT_DOSE_DAYS[doses_done]
    next_date = now_th() + timedelta(days=days_to_next)
    msg = (
        f"[ใบนัดฉีดวัคซีนกันพิษสุนัขบ้า] "
        f"คุณ \"{patient_name}\" "
        f"นัดฉีดวัคซีนกันพิษสุนัขบ้าเข็มที่ {next_dose} "
        f"ใน วันที่ {thai_date(next_date)}"
    )
    if next_dose < DOSE_COUNT:
        msg += f" และรับใบนัดฉีดเข็มที่ {next_dose + 1}"
    return msg


def build_patient_embed(
    patient_name: str,
    blood_type: str,
    gender: str,
    doctor_name: str,
    doses_done: int,
    image_url: str | None = None,
) -> discord.Embed:
    title = EMBED_TITLE_DONE if doses_done >= DOSE_COUNT else EMBED_TITLE_BASE

    embed = discord.Embed(
        title=title,
        description="[ข้อมูลผู้ป่วย]",
        color=discord.Color.from_rgb(0, 170, 255),
    )

    embed.add_field(name=FIELD_PATIENT_NAME, value=patient_name, inline=False)
    embed.add_field(name=FIELD_BLOOD, value=blood_type, inline=True)
    embed.add_field(name=FIELD_GENDER, value=gender, inline=True)
    embed.add_field(name=FIELD_STATUS_DOSES, value=build_dose_lines(doses_done), inline=False)
    embed.add_field(name=FIELD_STATUS_TEXT, value=build_status_text(patient_name, doses_done), inline=False)
    embed.add_field(name=FIELD_DOCTOR, value=doctor_name, inline=False)

    if image_url:
        embed.set_thumbnail(url=image_url)

    embed.timestamp = now_th()
    return embed


def parse_patient_embed(embed: discord.Embed) -> dict:
    """อ่าน state ผู้ป่วยจาก embed ของข้อความรายงาน"""
    data = {
        "patient_name": "ไม่ระบุ",
        "blood_type": "-",
        "gender": "-",
        "doctor_name": "-",
        "doses_done": 0,
        "image_url": None,
    }

    for field in embed.fields:
        if field.name == FIELD_PATIENT_NAME:
            data["patient_name"] = field.value
        elif field.name == FIELD_BLOOD:
            data["blood_type"] = field.value
        elif field.name == FIELD_GENDER:
            data["gender"] = field.value
        elif field.name == FIELD_STATUS_DOSES:
            data["doses_done"] = field.value.count("✅")
        elif field.name == FIELD_DOCTOR:
            data["doctor_name"] = field.value

    if embed.thumbnail and embed.thumbnail.url:
        data["image_url"] = embed.thumbnail.url

    return data


# ============================================================
# VIEW 1 — เลือกประเภทวัคซีน (ephemeral)
# ============================================================

class VaccineTypeView(ui.View):
    def __init__(self, attachment: discord.Attachment, requester_id: int):
        super().__init__(timeout=300)
        self.attachment = attachment
        self.requester_id = requester_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("⚠️ ปุ่มนี้ไม่ใช่ของคุณ", ephemeral=True)
            return False
        return True

    @ui.button(label="💉 วัคซีนพิษสุนัขบ้า", style=discord.ButtonStyle.primary)
    async def rabies_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RabiesVaccineModal(self.attachment))
        self.stop()

    @ui.button(label="💉 วัคซีนบาดทะยัก (เร็ว ๆ นี้)", style=discord.ButtonStyle.secondary, disabled=True)
    async def tetanus_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 ยังไม่เปิดให้ใช้งาน", ephemeral=True)


# ============================================================
# MODAL — ใบนัดฉีดวัคซีนพิษสุนัขบ้า
# ============================================================

class RabiesVaccineModal(ui.Modal, title="ใบนัดฉีดวัคซีนพิษสุนัขบ้า"):
    def __init__(self, attachment: discord.Attachment):
        super().__init__(timeout=600)
        self.attachment = attachment

        self.name_input = ui.TextInput(
            placeholder="ชื่อคนไข้",
            required=True,
            max_length=80,
        )

        self.blood_select = ui.Select(
            placeholder="เลือกกรุ๊ปเลือด",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="A", value="A"),
                discord.SelectOption(label="B", value="B"),
                discord.SelectOption(label="AB", value="AB"),
                discord.SelectOption(label="O", value="O"),
            ],
        )

        self.gender_select = ui.Select(
            placeholder="เลือกเพศ",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="ชาย", value="ชาย", emoji="👨"),
                discord.SelectOption(label="หญิง", value="หญิง", emoji="👩"),
            ],
        )

        self.add_item(ui.Label(text="ชื่อ - สกุล", component=self.name_input))
        self.add_item(ui.Label(text="กรุ๊ปเลือด", component=self.blood_select))
        self.add_item(ui.Label(text="เพศ", component=self.gender_select))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.attachment.url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ ไม่สามารถโหลดรูปได้", ephemeral=True)
                        return
                    data = await resp.read()
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดขณะโหลดรูป: {e}", ephemeral=True)
            return

        patient_name = self.name_input.value.strip()
        blood_type = self.blood_select.values[0]
        gender = self.gender_select.values[0]
        doctor_name = interaction.user.display_name

        file = discord.File(io.BytesIO(data), filename=self.attachment.filename)
        embed = build_patient_embed(
            patient_name=patient_name,
            blood_type=blood_type,
            gender=gender,
            doctor_name=doctor_name,
            doses_done=0,
            image_url=f"attachment://{self.attachment.filename}",
        )

        patient_msg = await interaction.followup.send(embed=embed, file=file, wait=True)

        treatment_view = RabiesTreatmentView()
        await interaction.channel.send(
            content=(
                "📋 **รายละเอียดการรักษา**\n"
                "กรุณากดปุ่มด้านล่างเพื่อบันทึกเข็มวัคซีนที่ฉีดในวันนี้"
            ),
            view=treatment_view,
            reference=patient_msg,
            mention_author=False,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        msg = f"❌ เกิดข้อผิดพลาด: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


# ============================================================
# VIEW 2 — ปุ่มควบคุมการรักษา (persistent, ไม่หมดเวลา)
# ============================================================

class RabiesTreatmentView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _fetch_patient_message(
        self, interaction: discord.Interaction
    ) -> discord.Message | None:
        ref = interaction.message.reference if interaction.message else None
        if not ref or not ref.message_id:
            await interaction.response.send_message(
                "❌ ไม่พบข้อความรายงานผู้ป่วยที่อ้างอิง", ephemeral=True
            )
            return None
        try:
            return await interaction.channel.fetch_message(ref.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "❌ ไม่สามารถโหลดข้อความรายงานผู้ป่วยได้", ephemeral=True
            )
            return None

    def _update_button_labels(self, doses_done: int):
        inject_btn = next((c for c in self.children if getattr(c, "custom_id", None) == CUSTOM_ID_INJECT), None)
        if inject_btn is None:
            return
        if doses_done >= DOSE_COUNT:
            inject_btn.label = "✅ ครบ 5 เข็มแล้ว"
            inject_btn.disabled = True
            inject_btn.style = discord.ButtonStyle.success
        else:
            inject_btn.label = f"💉 ฉีดเข็มที่ {doses_done + 1}"
            inject_btn.disabled = False
            inject_btn.style = discord.ButtonStyle.success

    @ui.button(
        label="💉 ฉีดเข็มที่ 1",
        style=discord.ButtonStyle.success,
        custom_id=CUSTOM_ID_INJECT,
    )
    async def inject_button(self, interaction: discord.Interaction, button: ui.Button):
        patient_msg = await self._fetch_patient_message(interaction)
        if patient_msg is None:
            return
        if not patient_msg.embeds:
            await interaction.response.send_message(
                "❌ ข้อความรายงานผู้ป่วยไม่มี Embed", ephemeral=True
            )
            return

        state = parse_patient_embed(patient_msg.embeds[0])

        if state["doses_done"] >= DOSE_COUNT:
            await interaction.response.send_message(
                "✅ ฉีดครบ 5 เข็มแล้ว ไม่สามารถฉีดเพิ่มได้", ephemeral=True
            )
            return

        new_doses_done = state["doses_done"] + 1
        new_embed = build_patient_embed(
            patient_name=state["patient_name"],
            blood_type=state["blood_type"],
            gender=state["gender"],
            doctor_name=state["doctor_name"],
            doses_done=new_doses_done,
            image_url=state["image_url"],
        )
        await patient_msg.edit(embed=new_embed)

        self._update_button_labels(new_doses_done)
        await interaction.response.edit_message(view=self)

    @ui.button(
        label="🔄 เริ่มใหม่",
        style=discord.ButtonStyle.danger,
        custom_id=CUSTOM_ID_RESET,
    )
    async def reset_button(self, interaction: discord.Interaction, button: ui.Button):
        patient_msg = await self._fetch_patient_message(interaction)
        if patient_msg is None:
            return
        if not patient_msg.embeds:
            await interaction.response.send_message(
                "❌ ข้อความรายงานผู้ป่วยไม่มี Embed", ephemeral=True
            )
            return

        state = parse_patient_embed(patient_msg.embeds[0])
        new_embed = build_patient_embed(
            patient_name=state["patient_name"],
            blood_type=state["blood_type"],
            gender=state["gender"],
            doctor_name=state["doctor_name"],
            doses_done=0,
            image_url=state["image_url"],
        )
        await patient_msg.edit(embed=new_embed)

        self._update_button_labels(0)
        await interaction.response.edit_message(view=self)


# ============================================================
# SLASH COMMAND
# ============================================================

@app_commands.command(name="วัคซีน", description="ระบบบันทึกการฉีดวัคซีน (พิษสุนัขบ้า / บาดทะยัก)")
@app_commands.describe(image="แนบรูปภาพประจำตัวผู้ป่วย")
async def vaccine(interaction: discord.Interaction, image: discord.Attachment):
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("❌ โปรดแนบเฉพาะไฟล์รูปภาพ", ephemeral=True)
        return

    view = VaccineTypeView(image, interaction.user.id)
    await interaction.response.send_message(
        "เลือกประเภทวัคซีนที่ต้องการบันทึก",
        view=view,
        ephemeral=True,
    )
