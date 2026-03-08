import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ฟังก์ชันวาดรูป
def process_card_image(profile_bytes, name, gender, phone, card_type):

    if card_type == "1 เดือน":
        template_path = "assets/template_2.jpg"
        color = (255, 255, 255)
    else:
        template_path = "assets/template.jpg"
        color = (0, 0, 0)

    font_path = "assets/Kanit-Regular.ttf"
    
    profile_img = Image.open(io.BytesIO(profile_bytes)).convert("RGBA")
    radius = 153
    size = (radius * 2, radius * 2)
    
    width, height = profile_img.size
    crop_size = min(width, height)
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    img_cropped = profile_img.crop((left, top, left + crop_size, top + crop_size))
    img_cropped = img_cropped.resize(size, Image.Resampling.LANCZOS)

    mask = Image.new('L', size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size[0], size[1]), fill=255)
    
    circular_face = Image.new('RGBA', size, (0, 0, 0, 0))
    circular_face.paste(img_cropped, (0, 0), mask=mask)

    now = datetime.now() + timedelta(hours=7)

    if card_type == "1 เดือน":
        expiry = now + relativedelta(months=1)
    else:
        expiry = now + timedelta(days=7)

    issue_date = now.strftime("%d/%m/%Y")
    issue_time = now.strftime("%H.%M น.")
    exp_date = expiry.strftime("%d/%m/%Y")
    exp_time = expiry.strftime("%H.%M น.")

    base = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, 28)

    base.paste(circular_face, (57, 72), circular_face)

    draw.text((472, 291), name, font=font, fill=color)
    draw.text((485, 340), gender, font=font, fill=color)
    draw.text((607, 391), phone, font=font, fill=color)
    draw.text((600, 441), issue_date, font=font, fill=color)
    draw.text((842, 441), issue_time, font=font, fill=color)
    draw.text((600, 489), exp_date, font=font, fill=color)
    draw.text((842, 489), exp_time, font=font, fill=color)

    output = io.BytesIO()
    base.save(output, format="PNG")
    output.seek(0)
    
    return output, issue_date, issue_time, exp_date, exp_time


# Dropdown เลือกระยะเวลา
class DurationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="7 วัน", value="7 วัน"),
            discord.SelectOption(label="1 เดือน", value="1 เดือน"),
        ]
        super().__init__(
            placeholder="เลือกระยะเวลาบัตร",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_duration = self.values[0]
        await interaction.response.defer()


# View สำหรับ dropdown
class DurationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_duration = "7 วัน"
        self.add_item(DurationSelect())


# Modal สำหรับกรอกข้อมูล
class InsuranceModal(discord.ui.Modal, title="แบบฟอร์มออกบัตรประกันสุขภาพ"):

    name_input = discord.ui.TextInput(label="ชื่อ-นามสกุล", placeholder="เช่น Prime McFly", required=True)
    gender_input = discord.ui.TextInput(label="เพศ", placeholder="ชาย / หญิง", required=True)
    phone_input = discord.ui.TextInput(label="เบอร์โทรศัพท์", placeholder="เช่น 98443", required=True)

    def __init__(self, attachment: discord.Attachment, card_type: str):
        super().__init__()
        self.attachment = attachment
        self.card_type = card_type

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer()

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(self.attachment.url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("❌ โหลดรูปไม่สำเร็จ", ephemeral=True)
                    profile_bytes = await resp.read()

            final_image, i_date, i_time, e_date, e_time = process_card_image(
                profile_bytes,
                self.name_input.value,
                self.gender_input.value,
                self.phone_input.value,
                self.card_type
            )

            embed = discord.Embed(title="💳 บัตรประจำตัว Pracharuk Care", color=discord.Color.blue())

            embed.add_field(name="👤 ชื่อ-นามสกุล", value=self.name_input.value, inline=True)
            embed.add_field(name="⚤ เพศ", value=self.gender_input.value, inline=True)
            embed.add_field(name="📞 เบอร์โทร", value=self.phone_input.value, inline=True)
            embed.add_field(name="📅 วันที่ออกบัตร", value=f"{i_date} | {i_time}", inline=False)
            embed.add_field(name="⏳ วันที่หมดอายุ", value=f"{e_date} | {e_time}", inline=False)

            embed.set_footer(text=f"ผู้ออกบัตร: {interaction.user.display_name}")
            
            file = discord.File(final_image, filename="insurance_card.png")
            embed.set_image(url="attachment://insurance_card.png")

            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)


# Slash Command
@app_commands.command(name="ออกบัตรประกัน", description="ออกบัตรประกันสุขภาพพร้อมรูปถ่าย")
@app_commands.describe(image="แนบรูปถ่ายหน้าตรง")
async def insurance(interaction: discord.Interaction, image: discord.Attachment):

    if not image.content_type or not image.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ โปรดแนบไฟล์รูปภาพเท่านั้น", ephemeral=True)

    view = DurationView()

    await interaction.response.send_message(
        "เลือกระยะเวลาบัตร",
        view=view,
        ephemeral=True
    )

    await view.wait()

    await interaction.followup.send_modal(
        InsuranceModal(image, view.selected_duration)
    )