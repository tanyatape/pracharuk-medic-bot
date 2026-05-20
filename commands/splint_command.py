import discord
from discord import app_commands
import aiohttp
import io


# ---------- MODAL ----------
class SplintModal(discord.ui.Modal, title="แบบฟอร์มรายงานการใส่เฝือก"):

    patient_name = discord.ui.TextInput(label="ชื่อผู้ป่วย",
                                        placeholder="กรอกชื่อ-สกุลผู้ป่วย",
                                        required=True)

    condition = discord.ui.TextInput(
        label="อาการ",
        placeholder="เช่น แขนขวาหัก กระดูกคอเคลื่อน",
        required=True)

    appointment_date = discord.ui.TextInput(
        label="วันที่นัด (รูปแบบ DD/MM/YYYY)",
        placeholder="เช่น 28/08/2025",
        required=True)

    appointment_time = discord.ui.TextInput(label="เวลานัด",
                                            placeholder="เช่น 10.00 น.",
                                            required=True)

    reason = discord.ui.TextInput(
        label="สาเหตุที่นัด",
        placeholder="เช่น นัดผ่าตัด และถอดเฝือกแข็ง ใส่เฝือกอ่อน",
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

        # 🔎 สร้างข้อความสรุป
        summary = (
            "**ใบนัด**\n"
            f"[ใบรายงานการใส่เฝือก] ผู้ป่วยชื่อ : {self.patient_name.value} "
            f"มีอาการ : {self.condition.value} | "
            f"นัดวันที่ {self.appointment_date.value} เวลา {self.appointment_time.value}"
            f"เนื่องจาก : {self.reason.value}")

        # ✅ Embed รายงาน
        embed = discord.Embed(title="🦴 รายงานการใส่เฝือก",
                              description=summary,
                              color=discord.Color.orange())

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
                        value=self.appointment_time.value,
                        inline=True)
        embed.add_field(name="📌 สาเหตุที่นัด",
                        value=self.reason.value,
                        inline=False)

        # แนบรูปและข้อมูลเพิ่มเติม
        embed.set_image(url=f"attachment://{self.attachment.filename}")
        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        await interaction.followup.send(embed=embed, file=file)


# ---------- SLASH COMMAND ----------
@app_commands.command(name="เฝือก",
                      description="แนบรูปและรายงานข้อมูลการใส่เฝือก")
@app_commands.describe(image="แนบรูปที่เกี่ยวข้องกับการใส่เฝือก")
async def splint(interaction: discord.Interaction, image: discord.Attachment):
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("❌ โปรดแนบเฉพาะไฟล์รูปภาพ",
                                                ephemeral=True)
        return

    modal = SplintModal(attachment=image)
    await interaction.response.send_modal(modal)
