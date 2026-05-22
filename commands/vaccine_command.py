# commands/vaccine_command.py

import discord
from discord import app_commands, ui
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import aiohttp
import io
import re

# ============================================================
# CONSTANTS
# ============================================================

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

DONE_EMOJI_BY_COUNT = {3: "3️⃣✅", 5: "5️⃣✅"}

# Field names (ใช้ทั้งตอนสร้างและ parse กลับ)
FIELD_PATIENT_NAME = "👤 ชื่อคนไข้"
FIELD_BLOOD = "🩸 กรุ๊ปเลือด"
FIELD_GENDER = "🦲 เพศ"
FIELD_STATUS_DOSES = "💉 สถานะวัคซีน"
FIELD_STATUS_TEXT = "📊 STATUS"
FIELD_DOCTOR = "👨‍⚕️ แพทย์ผู้ลงบันทึก"


# ============================================================
# VACCINE CONFIG
# ============================================================

@dataclass
class VaccineConfig:
    key: str
    display_name: str          # ใช้ในข้อความ "วัคซีนกัน{display_name}"
    title_base: str
    dose_count: int
    # intervals[N] = จำนวนวันที่เพิ่มไปอีก จากการฉีดเข็ม N เพื่อนัดเข็ม N+1
    intervals: Dict[int, int]
    inject_custom_id: str
    reset_custom_id: str
    color: discord.Color = field(default_factory=lambda: discord.Color.from_rgb(0, 170, 255))

    @property
    def title_done(self) -> str:
        emoji = DONE_EMOJI_BY_COUNT.get(self.dose_count, "✅")
        return f"{self.title_base} {emoji}"


RABIES_CONFIG = VaccineConfig(
    key="rabies",
    display_name="พิษสุนัขบ้า",
    title_base="🏥 ระบบวัคซีนป้องกันพิษสุนัขบ้า",
    dose_count=5,
    intervals={1: 3, 2: 4, 3: 7, 4: 16},
    inject_custom_id="vaccine_rabies_inject_v1",
    reset_custom_id="vaccine_rabies_reset_v1",
    color=discord.Color.from_rgb(0, 170, 255),
)

TETANUS_CONFIG = VaccineConfig(
    key="tetanus",
    display_name="บาดทะยัก",
    title_base="🏥 ระบบวัคซีนป้องกันบาดทะยัก",
    dose_count=3,
    intervals={1: 15, 2: 16},
    inject_custom_id="vaccine_tetanus_inject_v1",
    reset_custom_id="vaccine_tetanus_reset_v1",
    color=discord.Color.from_rgb(255, 165, 0),
)

ALL_CONFIGS = [RABIES_CONFIG, TETANUS_CONFIG]


def get_config_from_embed(embed: discord.Embed) -> Optional[VaccineConfig]:
    if not embed.title:
        return None
    for cfg in ALL_CONFIGS:
        if embed.title.startswith(cfg.title_base):
            return cfg
    return None


# ============================================================
# HELPERS — เวลา / ข้อความ
# ============================================================

def now_th() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=7)


def thai_date(dt: datetime) -> str:
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"


def short_thai_date(dt: datetime) -> str:
    return f"{dt.day:02d}/{dt.month:02d}/{dt.year + 543}"


DOSE_LINE_RE = re.compile(r"^(✅|⬜)\s*เข็มที่\s*(\d+)\s*(?:\((.+?)\))?\s*$")


def build_dose_lines(
    dose_count: int, doses_done: int, dose_dates: List[Optional[str]]
) -> str:
    lines: List[str] = []
    for i in range(1, dose_count + 1):
        if i <= doses_done:
            date_str = dose_dates[i - 1] if i - 1 < len(dose_dates) else None
            if date_str:
                lines.append(f"✅ เข็มที่ {i} ({date_str})")
            else:
                lines.append(f"✅ เข็มที่ {i}")
        else:
            lines.append(f"⬜ เข็มที่ {i}")
    return " ,\n".join(lines)


def parse_dose_lines(text: str) -> tuple[int, List[Optional[str]]]:
    doses_done = 0
    dates: List[Optional[str]] = []
    for raw in text.split(","):
        line = raw.strip()
        m = DOSE_LINE_RE.match(line)
        if not m:
            continue
        emoji, _idx, date_str = m.group(1), m.group(2), m.group(3)
        if emoji == "✅":
            doses_done += 1
            dates.append(date_str.strip() if date_str else None)
    return doses_done, dates


def build_status_text(cfg: VaccineConfig, patient_name: str, doses_done: int) -> str:
    if doses_done == 0:
        return "เริ่มต้นการรักษา"
    if doses_done >= cfg.dose_count:
        return f"✅ การรักษาเสร็จสมบูรณ์ (ฉีดครบ {cfg.dose_count} เข็ม)"

    next_dose = doses_done + 1
    days_to_next = cfg.intervals[doses_done]
    next_date = now_th() + timedelta(days=days_to_next)
    msg = (
        f"[ใบนัดฉีดวัคซีนกัน{cfg.display_name}] "
        f'คุณ "{patient_name}" '
        f"นัดฉีดวัคซีนกัน{cfg.display_name}เข็มที่ {next_dose} "
        f"ใน วันที่ {thai_date(next_date)}"
    )
    if next_dose < cfg.dose_count:
        msg += f" และรับใบนัดฉีดเข็มที่ {next_dose + 1}"
    return msg


# ============================================================
# EMBED BUILD / PARSE
# ============================================================

def build_patient_embed(
    cfg: VaccineConfig,
    patient_name: str,
    blood_type: str,
    gender: str,
    doctor_name: str,
    doses_done: int,
    dose_dates: List[Optional[str]],
    image_url: Optional[str] = None,
) -> discord.Embed:
    title = cfg.title_done if doses_done >= cfg.dose_count else cfg.title_base

    embed = discord.Embed(
        title=title,
        description="[ข้อมูลผู้ป่วย]",
        color=cfg.color,
    )

    embed.add_field(name=FIELD_PATIENT_NAME, value=patient_name, inline=False)
    embed.add_field(name=FIELD_BLOOD, value=blood_type, inline=True)
    embed.add_field(name=FIELD_GENDER, value=gender, inline=True)
    embed.add_field(
        name=FIELD_STATUS_DOSES,
        value=build_dose_lines(cfg.dose_count, doses_done, dose_dates),
        inline=False,
    )
    embed.add_field(
        name=FIELD_STATUS_TEXT,
        value=build_status_text(cfg, patient_name, doses_done),
        inline=False,
    )
    embed.add_field(name=FIELD_DOCTOR, value=doctor_name, inline=False)

    if image_url:
        embed.set_thumbnail(url=image_url)

    embed.timestamp = now_th()
    return embed


def parse_patient_embed(embed: discord.Embed) -> dict:
    data = {
        "patient_name": "ไม่ระบุ",
        "blood_type": "-",
        "gender": "-",
        "doctor_name": "-",
        "doses_done": 0,
        "dose_dates": [],
        "image_url": None,
    }

    for field_ in embed.fields:
        if field_.name == FIELD_PATIENT_NAME:
            data["patient_name"] = field_.value
        elif field_.name == FIELD_BLOOD:
            data["blood_type"] = field_.value
        elif field_.name == FIELD_GENDER:
            data["gender"] = field_.value
        elif field_.name == FIELD_STATUS_DOSES:
            doses_done, dose_dates = parse_dose_lines(field_.value)
            data["doses_done"] = doses_done
            data["dose_dates"] = dose_dates
        elif field_.name == FIELD_DOCTOR:
            data["doctor_name"] = field_.value

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
        await interaction.response.send_modal(
            VaccineModal(self.attachment, RABIES_CONFIG)
        )
        self.stop()

    @ui.button(label="💉 วัคซีนบาดทะยัก", style=discord.ButtonStyle.primary)
    async def tetanus_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            VaccineModal(self.attachment, TETANUS_CONFIG)
        )
        self.stop()


# ============================================================
# MODAL — ฟอร์มกรอกข้อมูลคนไข้ (ใช้ร่วมทุกวัคซีน)
# ============================================================

class VaccineModal(ui.Modal):
    def __init__(self, attachment: discord.Attachment, cfg: VaccineConfig):
        super().__init__(
            title=f"ใบนัดฉีดวัคซีน{cfg.display_name}",
            timeout=600,
        )
        self.attachment = attachment
        self.cfg = cfg

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
            cfg=self.cfg,
            patient_name=patient_name,
            blood_type=blood_type,
            gender=gender,
            doctor_name=doctor_name,
            doses_done=0,
            dose_dates=[],
            image_url=f"attachment://{self.attachment.filename}",
        )

        patient_msg = await interaction.followup.send(embed=embed, file=file, wait=True)

        if self.cfg.key == "rabies":
            treatment_view: ui.View = RabiesTreatmentView()
        else:
            treatment_view = TetanusTreatmentView()

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
# BASE TREATMENT VIEW (logic ร่วม) + subclass ต่อวัคซีน (persistent)
# ============================================================

class _BaseTreatmentView(ui.View):
    cfg: VaccineConfig  # override ใน subclass

    def __init__(self):
        super().__init__(timeout=None)

    async def _fetch_patient_message(
        self, interaction: discord.Interaction
    ) -> Optional[discord.Message]:
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

    def _resolve_cfg(self, embed: discord.Embed) -> VaccineConfig:
        # ใช้ cfg ที่ embed อ้างเป็นหลัก (กันกรณีปุ่ม persistent ถูกผูก embed ผิดประเภท)
        return get_config_from_embed(embed) or self.cfg

    def _update_button_labels(self, doses_done: int, cfg: VaccineConfig):
        inject_btn = next(
            (c for c in self.children if getattr(c, "custom_id", None) == cfg.inject_custom_id),
            None,
        )
        if inject_btn is None:
            return
        if doses_done >= cfg.dose_count:
            inject_btn.label = f"✅ ครบ {cfg.dose_count} เข็มแล้ว"
            inject_btn.disabled = True
            inject_btn.style = discord.ButtonStyle.success
        else:
            inject_btn.label = f"💉 ฉีดเข็มที่ {doses_done + 1}"
            inject_btn.disabled = False
            inject_btn.style = discord.ButtonStyle.success

    async def _handle_inject(self, interaction: discord.Interaction):
        patient_msg = await self._fetch_patient_message(interaction)
        if patient_msg is None:
            return
        if not patient_msg.embeds:
            await interaction.response.send_message(
                "❌ ข้อความรายงานผู้ป่วยไม่มี Embed", ephemeral=True
            )
            return

        embed = patient_msg.embeds[0]
        cfg = self._resolve_cfg(embed)
        state = parse_patient_embed(embed)

        if state["doses_done"] >= cfg.dose_count:
            await interaction.response.send_message(
                f"✅ ฉีดครบ {cfg.dose_count} เข็มแล้ว ไม่สามารถฉีดเพิ่มได้",
                ephemeral=True,
            )
            return

        new_doses_done = state["doses_done"] + 1
        new_dates = list(state["dose_dates"])
        # pad ให้พอดีจำนวน doses_done ก่อน (เผื่อ embed เก่าไม่มีวันที่)
        while len(new_dates) < state["doses_done"]:
            new_dates.append(None)
        new_dates.append(short_thai_date(now_th()))

        new_embed = build_patient_embed(
            cfg=cfg,
            patient_name=state["patient_name"],
            blood_type=state["blood_type"],
            gender=state["gender"],
            doctor_name=state["doctor_name"],
            doses_done=new_doses_done,
            dose_dates=new_dates,
            image_url=state["image_url"],
        )
        await patient_msg.edit(embed=new_embed)

        self._update_button_labels(new_doses_done, cfg)
        await interaction.response.edit_message(view=self)

    async def _handle_reset(self, interaction: discord.Interaction):
        patient_msg = await self._fetch_patient_message(interaction)
        if patient_msg is None:
            return
        if not patient_msg.embeds:
            await interaction.response.send_message(
                "❌ ข้อความรายงานผู้ป่วยไม่มี Embed", ephemeral=True
            )
            return

        embed = patient_msg.embeds[0]
        cfg = self._resolve_cfg(embed)
        state = parse_patient_embed(embed)

        new_embed = build_patient_embed(
            cfg=cfg,
            patient_name=state["patient_name"],
            blood_type=state["blood_type"],
            gender=state["gender"],
            doctor_name=state["doctor_name"],
            doses_done=0,
            dose_dates=[],
            image_url=state["image_url"],
        )
        await patient_msg.edit(embed=new_embed)

        self._update_button_labels(0, cfg)
        await interaction.response.edit_message(view=self)


class RabiesTreatmentView(_BaseTreatmentView):
    cfg = RABIES_CONFIG

    @ui.button(
        label="💉 ฉีดเข็มที่ 1",
        style=discord.ButtonStyle.success,
        custom_id=RABIES_CONFIG.inject_custom_id,
    )
    async def inject_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_inject(interaction)

    @ui.button(
        label="🔄 เริ่มใหม่",
        style=discord.ButtonStyle.danger,
        custom_id=RABIES_CONFIG.reset_custom_id,
    )
    async def reset_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_reset(interaction)


class TetanusTreatmentView(_BaseTreatmentView):
    cfg = TETANUS_CONFIG

    @ui.button(
        label="💉 ฉีดเข็มที่ 1",
        style=discord.ButtonStyle.success,
        custom_id=TETANUS_CONFIG.inject_custom_id,
    )
    async def inject_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_inject(interaction)

    @ui.button(
        label="🔄 เริ่มใหม่",
        style=discord.ButtonStyle.danger,
        custom_id=TETANUS_CONFIG.reset_custom_id,
    )
    async def reset_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_reset(interaction)


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
