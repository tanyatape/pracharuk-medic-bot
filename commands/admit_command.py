import discord
from discord import app_commands
import aiohttp
import io
from datetime import datetime


# ---------- MODAL ----------
class AdmitModal(discord.ui.Modal,
                 title="แบบฟอร์มรายงานการรับผู้ป่วยบาดเจ็บสาหัส"):

    patient_name = discord.ui.TextInput(label="ชื่อผู้ป่วยบาดเจ็บสาหัส",
                                        placeholder="กรอกชื่อ-สกุลผู้ป่วย",
                                        required=True)

    condition = discord.ui.TextInput(
        label="อาการ",
        placeholder="เช่น เส้นเสียงขาด ถูกทุบบริเวณท้ายทอย",
        required=True)

    appointment_date = discord.ui.TextInput(
        label="วันที่นัด (รูปแบบ DD/MM/YYYY)",
        placeholder="เช่น 29/08/2025",
        required=True)

    appointment_time = discord.ui.TextInput(label="เวลานัด",
                                            placeholder="เช่น 13:45 น.",
                                            required=True)

    reason = discord.ui.TextInput(
        label="สาเหตุที่นัด",
        placeholder="เช่น นัดผ่าตัดฉุกเฉิน หรือติดตามอาการ",
        required=True)

    def __init__(self, attachment: discord.Attachment):
        super().__init__()
        self.attachment = attachment

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # กัน timeout

        # โหลดรูป
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.attachment.url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "❌ ไม่สามารถโหลดรูปได้", ephemeral=True)
                        return
                    data = await resp.read()
                    file = discord.File(io.BytesIO(data),
                                        filename=self.attachment.filename)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดขณะโหลดรูป: {e}",
                                            ephemeral=True)
            return

        # วันที่และเวลาปัจจุบัน
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # 🔎 สร้างข้อความสรุป
        summary = (
            "**ใบนัด**\n"
            f"[ใบรับรองผู้ป่วยบาดเจ็บสาหัส] ผู้ป่วยชื่อ : {self.patient_name.value}\n"
            f"บาดเจ็บสาหัสวันที่ {now} น.\n"
            f"อาการ : {self.condition.value} | "
            f"นัดวันที่ {self.appointment_date.value} เวลา {self.appointment_time.value} น. "
            f"เนื่องจาก : {self.reason.value}")

        # ✅ Embed รายงาน
        embed = discord.Embed(title="🚑 รายงานรับผู้ป่วยบาดเจ็บสาหัส",
                              description=summary,
                              color=discord.Color.dark_red())

        # เพิ่ม field แยก
        embed.add_field(name="👤 ชื่อผู้ป่วย",
                        value=self.patient_name.value,
                        inline=False)
        embed.add_field(name="🩺 อาการ",
                        value=self.condition.value,
                        inline=False)
        embed.add_field(name="🗓️ วันที่นัด",
                        value=self.appointment_date.value,
                        inline=True)
        embed.add_field(name="⏰ เวลานัด",
                        value=self.appointment_time.value + " น.",
                        inline=True)
        embed.add_field(name="📌 สาเหตุที่นัด",
                        value=self.reason.value,
                        inline=False)
        embed.add_field(name="🕓 เวลาที่บาดเจ็บสาหัส",
                        value=now + " น.",
                        inline=False)

        embed.set_image(url=f"attachment://{self.attachment.filename}")
        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        await interaction.followup.send(embed=embed, file=file)


# ---------- SLASH COMMAND ----------
@app_commands.command(name="เคสพิเศษ",
                      description="แนบรูปและรายงานข้อมูลผู้ป่วยบาดเจ็บสาหัส")
@app_commands.describe(image="แนบรูปภาพผู้ป่วยหรือเอกสารที่เกี่ยวข้อง")
async def admit(interaction: discord.Interaction, image: discord.Attachment):
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("❌ โปรดแนบเฉพาะไฟล์รูปภาพ",
                                                ephemeral=True)
        return

    modal = AdmitModal(attachment=image)
    await interaction.response.send_modal(modal)
