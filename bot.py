# main.py

import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

if os.environ.get("RAILWAY_ENVIRONMENT") is None:
    load_dotenv()

from commands.dna_command import matchdna, crimedna
from commands.drug_command import drug
from commands.splint_command import splint
from commands.admit_command import admit
from commands.delete_command import delete_command
from commands.help_command import help_command
from commands.off_duty_command import offduty
from commands.cancer_command import cancer
from handlers.duty_handler import handle_on_message

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return await bot.is_owner(interaction.user)
    return app_commands.check(predicate)


@bot.event
async def on_ready():
    print(f"✅ Bot is ready as {bot.user}")
    try:
        # เพิ่มคำสั่ง
        bot.tree.add_command(matchdna)
        bot.tree.add_command(crimedna)
        bot.tree.add_command(drug)
        bot.tree.add_command(splint)
        bot.tree.add_command(admit)
        bot.tree.add_command(delete_command)
        bot.tree.add_command(help_command)
        bot.tree.add_command(offduty)
        bot.tree.add_command(cancer)

        # 🔄 ซิงค์คำสั่งทั้งหมด (global)
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("💊ยาบ้า ยาบ้า ยานรก 💊"))


@bot.tree.command(name="reload", description="รีโหลดคำสั่งบอท")
@is_owner()
async def reload(interaction: discord.Interaction):
    try:
        await bot.tree.sync(guild=None)
        await interaction.response.send_message("♻️ รีโหลดคำสั่งเรียบร้อยแล้ว!")
    except Exception as e:
        await interaction.response.send_message(f"❌ ไม่สามารถรีโหลดคำสั่งได้: {e}")


@bot.tree.command(name="restart", description="รีสตาร์ทบอท")
@is_owner()
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("♻️ กำลังรีสตาร์ทบอท...")
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)


@bot.event
async def on_message(message: discord.Message):
    await handle_on_message(message, bot)
    await bot.process_commands(message)


bot.run(TOKEN)
