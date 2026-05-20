# commands/cancer_command.py

import discord
from discord import app_commands
from datetime import datetime
import aiohttp
import io


# ---------- Modal 1 ----------
class CancerModal1(discord.ui.Modal, title="ข้อมูลผู้ป่วยมะเร็ง (1/2)"):
    patient_name = discord.ui.TextInput(
        label="ชื่อผู้ป่วย",
        placeholder="กรอกชื่อ-สกุลผู้ป่วย",
        required=True
    )
    cancer_stage = discord.ui.TextInput(
        label="วินิจฉัยมะเร็งระดับ",
        placeholder="1 / 2 / 3 / 4",
        required=True,
        max_length=1
    )
    symptoms = discord.ui.TextInput(
        label="อาการ",
        placeholder="อาการของผู้ป่วย",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, attachment: discord.Attachment):
        super().__init__()
        self.attachment = attachment

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            content="✅ ขั้นตอนที่ 1 เสร็จสิ้น กดปุ่มด้านล่างเพื่อกรอกข้อมูลขั้นตอนที่ 2",
            view=CancerStep2Button(
                attachment=self.attachment,
                patient_name=self.patient_name.value,
                cancer_stage=self.cancer_stage.value,
                symptoms=self.symptoms.value
            ),
            ephemeral=True
        )


# ---------- Button View เปิด Modal 2 ----------
class CancerStep2Button(discord.ui.View):
    def __init__(self, attachment, patient_name, cancer_stage, symptoms):
        super().__init__(timeout=None)
        self.attachment = attachment
        self.patient_name = patient_name
        self.cancer_stage = cancer_stage
        self.symptoms = symptoms

    @discord.ui.button(label="ไปต่อขั้นตอนที่ 2", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            CancerModal2(
                attachment=self.attachment,
                patient_name=self.patient_name,
                cancer_stage=self.cancer_stage,
                symptoms=self.symptoms
            )
        )


# ---------- Modal 2 ----------
class CancerModal2(discord.ui.Modal, title="ข้อมูลผู้ป่วยมะเร็ง (2/2)"):
    treatment = discord.ui.TextInput(
        label="การรักษา",
        placeholder="เช่น การผ่าตัด / เคมีบำบัด / รังสีรักษา",
        style=discord.TextStyle.paragraph,
        required=True
    )
    appointment_date = discord.ui.TextInput(
        label="วันที่นัด (รูปแบบ DD/MM/YYYY - DD/MM/YYYY)",
        placeholder="เช่น 04/09/2025 - 08/09/2025",
        required=True
    )
    appointment_time = discord.ui.TextInput(
        label="เวลาที่นัด",
        placeholder="เช่น 12.00 น.",
        required=True
    )

    def __init__(self, attachment: discord.Attachment, patient_name: str, cancer_stage: str, symptoms: str):
        super().__init__()
        self.attachment = attachment
        self.patient_name = patient_name
        self.cancer_stage = cancer_stage
        self.symptoms = symptoms

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # โหลดรูป
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.attachment.url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "❌ ไม่สามารถโหลดรูปได้", ephemeral=True)
                        return
                    data = await resp.read()
                    file = discord.File(io.BytesIO(data), filename=self.attachment.filename)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดขณะโหลดรูป: {e}", ephemeral=True)
            return

        # เวลาปัจจุบันแบบไทย
        now = datetime.utcnow()
        now_thai = now.astimezone(datetime.now().astimezone().tzinfo)  # local timezone
        timestamp_str = now_thai.strftime("%d.%m.%Y - %H:%M:%S")

        # สร้างข้อความสรุป
        summary = (
            f"**[ใบนัดผู้ป่วยมะเร็ง]**\n"
            f"ผู้ป่วยชื่อ : {self.patient_name} ได้รับการวินิจฉัยว่าเป็นมะเร็งปอดระดับ {self.cancer_stage} | "
            f"มีอาการ {self.symptoms} ต้องได้รับการรักษาโดย {self.treatment.value} | "
            f"นัดวันที่ {self.appointment_date.value} เวลา {self.appointment_time.value}"
        )

        # สร้าง Embed
        embed = discord.Embed(
            title="🩺 รายงานผู้ป่วยมะเร็ง",
            description=summary,
            color=discord.Color.purple()
        )

        embed.add_field(name="👤 ชื่อผู้ป่วย", value=self.patient_name, inline=False)
        embed.add_field(name="🔬 ระดับมะเร็ง", value=self.cancer_stage, inline=True)
        embed.add_field(name="🩹 อาการ", value=self.symptoms, inline=False)
        embed.add_field(name="💊 การรักษา", value=self.treatment.value, inline=False)
        embed.add_field(name="🗓️ วันที่นัด", value=self.appointment_date.value, inline=True)
        embed.add_field(name="⏰ เวลาที่นัด", value=self.appointment_time.value, inline=True)

        embed.set_image(url=f"attachment://{self.attachment.filename}")
        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        await interaction.followup.send(embed=embed, file=file)


# ---------- Slash Command ----------
@app_commands.command(
    name="มะเร็ง",
    description="แนบรูปและรายงานข้อมูลผู้ป่วยมะเร็ง"
)
@app_commands.describe(image="แนบรูปที่เกี่ยวข้องกับผู้ป่วยมะเร็ง")
async def cancer(interaction: discord.Interaction, image: discord.Attachment):
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("❌ โปรดแนบเฉพาะไฟล์รูปภาพ", ephemeral=True)
        return

    modal = CancerModal1(attachment=image)
    await interaction.response.send_modal(modal)
