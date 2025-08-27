import discord
from discord import app_commands
import os

DELETE_CODE = os.getenv("DELETE_CODE")


class DeleteEmbedModal(discord.ui.Modal, title="ลบข้อความ Embed ของบอท"):
    message_id = discord.ui.TextInput(
        label="Message ID ที่ต้องการลบ",
        placeholder="ใส่ message_id เช่น 123456789012345678",
        required=True)

    password = discord.ui.TextInput(label="รหัสผ่านลบ",
                                    placeholder="กรอกรหัสที่ตั้งไว้",
                                    required=True,
                                    style=discord.TextStyle.short)

    def __init__(self, bot: discord.Client):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if self.password.value != DELETE_CODE:
            await interaction.followup.send("❌ รหัสผ่านไม่ถูกต้อง",
                                            ephemeral=True)
            return

        try:
            msg = await interaction.channel.fetch_message(
                int(self.message_id.value))
        except discord.NotFound:
            await interaction.followup.send("❌ ไม่พบข้อความ", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("❌ ไม่มีสิทธิ์เข้าถึงข้อความ",
                                            ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.followup.send("❌ ข้อผิดพลาดในการโหลดข้อความ",
                                            ephemeral=True)
            return

        if msg.author.id != self.bot.user.id:
            await interaction.followup.send("❌ ข้อความนี้ไม่ได้มาจากบอท",
                                            ephemeral=True)
            return

        if not msg.embeds:
            await interaction.followup.send("⚠️ ข้อความไม่มี Embed",
                                            ephemeral=True)
            return

        try:
            for embed in msg.embeds:
                embed_copy = discord.Embed.from_dict(embed.to_dict())
                await interaction.user.send("📩 Embed ที่คุณลบ:",
                                            embed=embed_copy)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ไม่สามารถส่ง DM ได้ กรุณาเปิด DM", ephemeral=True)
            return

        try:
            await msg.delete()
        except discord.Forbidden:
            await interaction.followup.send("❌ ไม่มีสิทธิ์ลบข้อความ",
                                            ephemeral=True)
            return

        await interaction.followup.send(
            "✅ ลบข้อความเรียบร้อย และส่ง Embed ไปยัง DM ของคุณแล้ว",
            ephemeral=True)


@app_commands.command(name="ลบข้อความ",
                      description="ลบข้อความบอทด้วย Message ID และรหัสผ่าน")
async def delete_command(interaction: discord.Interaction):
    modal = DeleteEmbedModal(interaction.client)
    await interaction.response.send_modal(modal)
