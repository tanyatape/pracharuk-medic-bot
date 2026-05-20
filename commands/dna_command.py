import discord
from discord.ui import Modal, TextInput, View, Button
from discord.ext import commands
from discord import app_commands

# เก็บข้อมูลชั่วคราวสำหรับผู้ใช้แต่ละคน
user_states = {}


class NextMatchStepView(View):

    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="กรอกข้อมูลขั้นตอนที่ 2",
                       style=discord.ButtonStyle.primary)
    async def next_step(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ ปุ่มนี้ไม่ใช่ของคุณ!",
                                                    ephemeral=True)
            return
        await interaction.response.send_modal(MatchDNA_Modal2())


class MatchDNA_Modal1(Modal):

    def __init__(self):
        super().__init__(title="Match DNA - ขั้นตอนที่ 1")

        self.victim = TextInput(label="ชื่อผู้บาดเจ็บหมดสภาพ")
        self.gender = TextInput(label="เพศของผู้ก่อเหตุ")
        self.hair_color = TextInput(label="สีผมของผู้ก่อเหตุ")
        self.blood_type = TextInput(label="กรุ๊ปเลือดของผู้ก่อเหตุ")
        self.dna_number = TextInput(label="หมายเลขซอง DNA อาชญากรรม")

        self.add_item(self.victim)
        self.add_item(self.gender)
        self.add_item(self.hair_color)
        self.add_item(self.blood_type)
        self.add_item(self.dna_number)

    async def on_submit(self, interaction: discord.Interaction):
        user_states[interaction.user.id] = {
            "victim": self.victim.value,
            "gender": self.gender.value,
            "hair_color": self.hair_color.value,
            "blood_type": self.blood_type.value,
            "dna_number": self.dna_number.value
        }

        await interaction.response.send_message(
            "✅ รับข้อมูลขั้นตอนที่ 1 เรียบร้อย! กรุณากดปุ่มด้านล่างเพื่อกรอกข้อมูลขั้นตอนที่ 2",
            view=NextMatchStepView(interaction.user.id),
            ephemeral=True)


class MatchDNA_Modal2(Modal):

    def __init__(self):
        super().__init__(title="Match DNA - ขั้นตอนที่ 2")

        self.suspect_name = TextInput(label="ชื่อผู้ก่อเหตุ")
        self.notes = TextInput(label="หมายเหตุเพิ่มเติม", required=False)

        self.add_item(self.suspect_name)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        state = user_states.get(interaction.user.id)
        if not state:
            await interaction.response.send_message(
                "⚠️ ไม่พบข้อมูลจากขั้นตอนก่อนหน้า กรุณาเริ่มใหม่อีกครั้ง",
                ephemeral=True)
            return

        description = (f"[ใบรับรองการ Match DNA] "
                       f"ผู้เสียหายชื่อ : {state['victim']} | "
                       f"ถูกทำร้ายร่างกายจนหมดสภาพโดยผู้ต้องสงสัย "
                       f"เพศ : {state['gender']} "
                       f"สีผม : {state['hair_color']} "
                       f"กรุ๊ปเลือด : {state['blood_type']} | "
                       f"ซึ่งตรงกับบุคคลชื่อ : {self.suspect_name.value} | "
                       f"หมายเลขซอง DNA อาชญากรรม : {state['dna_number']}")

        if self.notes.value:
            description += f"\nหมายเหตุ : {self.notes.value}"

        embed = discord.Embed(title="Match DNA Report",
                              description=description,
                              color=discord.Color.blue(),
                              timestamp=interaction.created_at)

        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        await interaction.response.send_message(embed=embed)
        user_states.pop(interaction.user.id, None)


class NextCrimeStepView(View):

    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="กรอกข้อมูลขั้นตอนที่ 2",
                       style=discord.ButtonStyle.danger)
    async def next_crime_step(self, interaction: discord.Interaction,
                              button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ ปุ่มนี้ไม่ใช่ของคุณ!",
                                                    ephemeral=True)
            return
        await interaction.response.send_modal(CrimeDNA_Modal2())


class CrimeDNA_Modal1(Modal):

    def __init__(self):
        super().__init__(title="Crime DNA - ขั้นตอนที่ 1")

        self.victim = TextInput(label="ชื่อผู้เสียหาย", row=0)
        self.dna_number = TextInput(label="หมายเลขซอง DNA อาชญากรรม", row=1)

        self.add_item(self.victim)
        self.add_item(self.dna_number)

    async def on_submit(self, interaction: discord.Interaction):
        user_states[interaction.user.id] = {
            "victim": self.victim.value,
            "dna_number": self.dna_number.value
        }

        await interaction.response.send_message(
            "✅ รับข้อมูลขั้นตอนที่ 1 เรียบร้อย! กรุณากดปุ่มด้านล่างเพื่อกรอกข้อมูลขั้นตอนที่ 2",
            view=NextCrimeStepView(interaction.user.id),
            ephemeral=True)


class CrimeDNA_Modal2(Modal):

    def __init__(self):
        super().__init__(title="Crime DNA - ขั้นตอนที่ 2")

        self.gender = TextInput(label="เพศของผู้ก่อเหตุ", row=0)
        self.hair_color = TextInput(label="สีผมของผู้ก่อเหตุ", row=1)
        self.blood_type = TextInput(label="กรุ๊ปเลือดของผู้ก่อเหตุ", row=2)
        self.notes = TextInput(label="หมายเหตุเพิ่มเติม (ถ้ามี)",
                               required=False,
                               style=discord.TextStyle.paragraph,
                               row=3)

        self.add_item(self.gender)
        self.add_item(self.hair_color)
        self.add_item(self.blood_type)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        state = user_states.get(interaction.user.id)
        if not state:
            await interaction.response.send_message(
                "⚠️ ไม่พบข้อมูลจากขั้นตอนก่อนหน้า กรุณาเริ่มใหม่อีกครั้ง",
                ephemeral=True)
            return

        description = (f"[ใบรับรองการตรวจสอบ DNA อาชญากรรม] "
                       f"ผู้เสียหายชื่อ : {state['victim']} | "
                       f"ถูกทำร้ายร่างกายโดยผู้ต้องสงสัย "
                       f"เพศ : {self.gender.value} "
                       f"สีผม : {self.hair_color.value} "
                       f"กรุ๊ปเลือด : {self.blood_type.value} | "
                       f"หมายเลขซอง DNA อาชญากรรม : {state['dna_number']}")

        if self.notes.value:
            description += f"\nหมายเหตุ : {self.notes.value}"

        embed = discord.Embed(title="Crime DNA Report",
                              description=description,
                              color=discord.Color.red(),
                              timestamp=interaction.created_at)
        embed.set_footer(text=f"อัปโหลดโดย: {interaction.user.display_name}")
        embed.timestamp = interaction.created_at

        await interaction.response.send_message(embed=embed)
        user_states.pop(interaction.user.id, None)


@app_commands.command(name="แมชdna", description="กรอกข้อมูลการ Match DNA")
async def matchdna(interaction: discord.Interaction):
    await interaction.response.send_modal(MatchDNA_Modal1())


@app_commands.command(name="ตรวจdna",
                      description="กรอกข้อมูลการตรวจสอบ DNA อาชฐากรรม")
async def crimedna(interaction: discord.Interaction):
    await interaction.response.send_modal(CrimeDNA_Modal1())


async def setup(bot: commands.Bot):
    bot.tree.add_command(matchdna)
    bot.tree.add_command(crimedna)
