import discord
from discord import app_commands
from datetime import datetime, timedelta, timezone

# ---------- MODAL ----------
class OffDutyModal(discord.ui.Modal, title="แบบฟอร์มแจ้ง Off Duty (นอกเมือง)"):

    name = discord.ui.TextInput(
        label="ชื่อของคุณ",
        placeholder="กรอกชื่อ-สกุล (เช่น Prime McFly)",
        required=True
    )

    reason = discord.ui.TextInput(
        label="เหตุผล",
        style=discord.TextStyle.paragraph,
        placeholder="อธิบายเหตุผลที่ไม่สามารถเข้าเมืองได้",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # ✅ เวลาปัจจุบัน (UTC+7) = เวลาไทย
        tz_th = timezone(timedelta(hours=7))
        now_th = datetime.now(tz=tz_th)

        timestamp_str = now_th.strftime("%d.%m.%Y - %H:%M:%S")

        # ✅ สร้าง Embed
        embed = discord.Embed(
            title=self.name.value,
            description="Off duty",
            color=discord.Color.red()
        )

        embed.add_field(name="เหตุผล", value=self.reason.value, inline=False)
        embed.set_footer(text=f"เวลา : {timestamp_str}")
        embed.timestamp = now_th  # แสดงเวลาเป็น UTC (Discord บังคับ)

        await interaction.followup.send(embed=embed)

@app_commands.command(
    name="offduty",
    description="แจ้ง Off Duty กรณีอยู่นอกเมือง"
)
async def offduty(interaction: discord.Interaction):
    modal = OffDutyModal()
    await interaction.response.send_modal(modal)
