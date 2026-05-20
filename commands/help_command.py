import discord
from discord import app_commands


@app_commands.command(name="คำสั่ง",
                      description="แสดงรายการคำสั่งทั้งหมดของบอท")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="รวมคำสั่งสำหรับบอท Pracharuk Medic",
        color=0x0AF,  # หรือใช้ 2815 ถ้าอยากให้ตรงกับ JSON (0x0AF = 2815)
    )

    embed.add_field(name="/เคสพิเศษ",
                    value="กรอกข้อมูลและทำใบนัดเคสพิเศษที่ต้องแอดมิท",
                    inline=False)
    embed.add_field(name="/ยาเสพติด",
                    value="กรอกข้อมูลและทำใบนัดเพื่อบำบัดผู้ติดสารเสพติด",
                    inline=False)
    embed.add_field(
        name="/เฝือก",
        value="กรอกข้อมูลและทำใบนัดเพื่อใส่เฝือก ถอดเฝือก หรือผ่าตัด",
        inline=False)
    embed.add_field(name="/แมชdna",
                    value="ใบรับรองการ Match DNA",
                    inline=False)
    embed.add_field(name="/ตรวจdna",
                    value="ใบรับรองการตรวจ DNA อาชญากรรม",
                    inline=False)

    embed.set_thumbnail(
        url=
        "https://cdn.discordapp.com/avatars/1284559774557409342/4e8e1f39efb438c295a49a533b39fce5?size=1024"
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)
