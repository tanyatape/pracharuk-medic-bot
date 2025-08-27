# commands/drug_command.py

import discord
from discord import app_commands
import aiohttp
import io


class DrugModal(discord.ui.Modal, title="แบบฟอร์มรายงานผลตรวจสารเสพติด"):

    patient_name = discord.ui.TextInput(label="ชื่อผู้ป่วย",
                                        placeholder="กรอกชื่อ-สกุลผู้ป่วย",
                                        required=True)

    drug_level = discord.ui.TextInput(
        label="ระดับสารเสพติด (ต่ำ / กลาง / สูง)",
        placeholder="เช่น ต่ำ",
        required=True)

    session_number = discord.ui.TextInput(label="นัดเข้ารับการบำบัดครั้งที่",
                                          placeholder="กรอกตัวเลข เช่น 1",
                                          required=True)

    appointment_date = discord.ui.TextInput(
        label="วันที่นัด (รูปแบบ DD/MM/YYYY)",
        placeholder="เช่น 27/08/2025",
        required=True)

    appointment_time = discord.ui.TextInput(label="เวลานัด (รูปแบบ HH:MM)",
                                            placeholder="เช่น 14:30",
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

        # สร้างข้อความสรุป (description)
        summary = (
            "**ใบนัด**\n"
            f"[ใบรับรองการตรวจสารเสพติด] ผู้ป่วยชื่อ : {self.patient_name.value} "
            f"ได้ตรวจพบสารเสพติดระดับ : {self.drug_level.value} | "
            f"นัดเพื่อเข้ารับการบำบัดสารเสพติดครั้งที่ {self.session_number.value} "
            f"วันที่ {self.appointment_date.value} เวลา {self.appointment_time.value} น."
        )

        # สร้าง Embed
        embed = discord.Embed(title="🧪 รายงานผลตรวจสารเสพติด",
                              description=summary,
                              color=discord.Color.red())

        # เพิ่ม fields แยก
        embed.add_field(name="👤 ชื่อผู้ป่วย",
                        value=self.patient_name.value,
                        inline=False)
        embed.add_field(name="📊 ระดับสารเสพติด",
                        value=self.drug_level.value,
                        inline=True)
        embed.add_field(name="🔁 ครั้งที่",
                        value=self.session_number.value,
                        inline=True)
        embed.add_field(name="🗓️ วันที่นัด",
                        value=self.appointment_date.value,
                        inline=True)
        embed.add_field(name="⏰ เวลานัด",
                        value=self.appointment_time.value + " น.",
                        inline=True)

        # รูปภาพ / footer / timestamp
        embed.set_image(url=f"attachment://{self.attachment.filename}")
        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        # ส่งข้อความกลับ
        await interaction.followup.send(embed=embed, file=file)


# ---------- SLASH COMMAND ----------
@app_commands.command(name="ยาเสพติด",
                      description="แนบรูปผลตรวจและกรอกข้อมูลผู้ป่วย")
@app_commands.describe(image="แนบรูปผลตรวจสารเสพติด")
async def drug(interaction: discord.Interaction, image: discord.Attachment):
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("❌ โปรดแนบเฉพาะไฟล์รูปภาพ",
                                                ephemeral=True)
        return

    modal = DrugModal(attachment=image)
    await interaction.response.send_modal(modal)
