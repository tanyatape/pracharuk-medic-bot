import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button, Button  # ✅ เพิ่ม Button ที่คุณลืม
import os
from pymongo import MongoClient
from typing import List

# ✅ MongoDB connection
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client["pracharuk_medic"]
collection = db["Surgery"]

# ✅ Pagination config
ITEMS_PER_PAGE = 10


def build_embed(name: str, records: List[dict], page: int) -> discord.Embed:
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_records = records[start_idx:end_idx]

    embed = discord.Embed(
        title=f"ประวัติการศัลยกรรมของ {name}",
        color=discord.Color.teal()
    )

    for i, record in enumerate(page_records, start=start_idx + 1):
        embed.add_field(
            name=f"ครั้งที่ {i} | ศัลยกรรมโดย {record['ชื่อแพทย์']}",
            value=f"วันที่ {record['วันที่ศัลยกรรม']} เวลา {record['เวลาที่ศัลยกรรม']} น.",
            inline=False
        )

    embed.set_footer(text=f"หน้า {page + 1} จาก {((len(records) - 1) // ITEMS_PER_PAGE) + 1}")
    return embed


class SurgeryHistoryView(View):
    def __init__(self, interaction: discord.Interaction, name: str, records: List[dict]):
        super().__init__(timeout=120)
        self.interaction = interaction
        self.name = name
        self.records = records
        self.current_page = 0
        self.total_pages = (len(records) - 1) // ITEMS_PER_PAGE

        self.previous_button = Button(label="⬅️ ก่อนหน้า", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="➡️ ถัดไป", style=discord.ButtonStyle.primary)

        self.previous_button.callback = self.previous
        self.next_button.callback = self.next

        self.add_item(self.previous_button)
        self.add_item(self.next_button)

        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages

    async def previous(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ คุณไม่ได้เป็นคนเรียกคำสั่งนี้", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        embed = build_embed(self.name, self.records, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def next(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ คุณไม่ได้เป็นคนเรียกคำสั่งนี้", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        embed = build_embed(self.name, self.records, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)


@app_commands.command(name="ศัลยกรรม", description="ดูประวัติการศัลยกรรมของผู้ใช้บริการ")
@app_commands.describe(name="ชื่อผู้ใช้บริการที่ต้องการตรวจสอบ")
async def surgery(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)

    results = list(collection.find({"ชื่อผู้ใช้บริการ": name}))

    if not results:
        await interaction.followup.send(f"❌ ไม่พบประวัติการศัลยกรรมของ {name}", ephemeral=True)
        return

    embed = build_embed(name, results, 0)
    view = SurgeryHistoryView(interaction, name, results)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ใช้สำหรับโหลด command เข้า bot
async def setup(bot: commands.Bot):
    bot.tree.add_command(surgery)
