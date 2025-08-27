import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
from datetime import datetime

from commands.dna_command import matchdna, crimedna
from commands.drug_command import drug
from commands.splint_command import splint
from commands.admit_command import admit
from commands.delete_command import delete_command
from commands.help_command import help_command

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

SOURCE_CHANNEL_ID = 1115872528771055727
TARGET_CHANNEL_ID = 1409388670242394172


def is_owner():

    async def predicate(interaction: discord.Interaction) -> bool:
        return await bot.is_owner(interaction.user)

    return app_commands.check(predicate)


@bot.event
async def on_ready():
    print(f"✅ Bot is ready as {bot.user}")
    try:
        bot.tree.add_command(matchdna)
        bot.tree.add_command(crimedna)
        bot.tree.add_command(drug)
        bot.tree.add_command(splint)
        bot.tree.add_command(admit)
        bot.tree.add_command(delete_command)
        bot.tree.add_command(help_command)
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    print("🔍 Monitoring Embed messages...")
    activity = discord.Game("💊ยาบ้า ยาบ้า ยานรก 💊")
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.tree.command(name="reload", description="รีโหลดคำสั่งบอท")
@is_owner()
async def reload(interaction: discord.Interaction):
    try:
        await bot.tree.sync(guild=None)
        await interaction.response.send_message("♻️ รีโหลดคำสั่งเรียบร้อยแล้ว!"
                                                )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ ไม่สามารถรีโหลดคำสั่งได้: {e}")


@bot.tree.command(name="restart", description="รีสตาร์ทบอท")
@is_owner()
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("♻️ กำลังรีสตาร์ทบอท...")
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)


def parse_footer_time(footer_text):
    try:
        prefix = "เวลา : "
        time_str = footer_text.replace(prefix, "")
        return datetime.strptime(time_str, "%d.%m.%Y - %H:%M:%S")
    except Exception as e:
        print(f"❌ Failed to parse time: {e}")
        return None


@bot.event
async def on_message(message: discord.Message):
    print(
        f"[DEBUG] New message in channel {message.channel.id} by {message.author}"
    )

    if message.webhook_id:
        print("[DEBUG] Message sent by webhook.")

    if message.channel.id != SOURCE_CHANNEL_ID:
        print("[DEBUG] Message is not in the monitored source channel.")
        return

    if not message.embeds:
        print("[DEBUG] No embed found in message.")
        return

    embed = message.embeds[0]
    title = embed.title
    description = embed.description
    footer_text = embed.footer.text if embed.footer else None

    print(
        f"[DEBUG] Embed details: title={title}, desc={description}, footer={footer_text}"
    )

    if not all([title, description, footer_text]):
        print("[DEBUG] Embed missing title/description/footer.")
        return

    if description.lower() == "off duty":
        off_time = parse_footer_time(footer_text)
        if not off_time:
            print("[DEBUG] Could not parse off_time.")
            return

        found = False
        async for msg in message.channel.history(limit=100):
            if msg.id == message.id or not msg.embeds:
                continue

            prev_embed = msg.embeds[0]
            if (prev_embed.title == title
                    and prev_embed.description.lower() == "on duty"
                    and prev_embed.footer and prev_embed.footer.text):
                on_time = parse_footer_time(prev_embed.footer.text)
                if not on_time:
                    continue

                duration = off_time - on_time
                total_seconds = int(duration.total_seconds())
                hours = total_seconds / 3600

                print(f"[CALC] คำนวณเวลา {hours:.2f} ชั่วโมงสำหรับ {title}")

                result_embed = discord.Embed(
                    title=title,
                    description=f"เวลาการทำงาน {hours:.2f} ชั่วโมง",
                    color=discord.Color.blue())
                result_embed.set_footer(text="Approved by Pracharuck Medic")
                result_embed.timestamp = datetime.utcnow()

                target_channel = bot.get_channel(TARGET_CHANNEL_ID)
                if target_channel:
                    await target_channel.send(embed=result_embed)
                else:
                    print(f"❌ Target channel not found: {TARGET_CHANNEL_ID}")

                found = True
                break

        if not found:
            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                await target_channel.send(
                    f"⚠️ ไม่พบข้อมูล On Duty ล่าสุดของ **{title}** เพื่อคำนวณเวลา"
                )

    await bot.process_commands(message)

bot.run(TOKEN)
