import discord
from discord.ext import commands
from discord import app_commands

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID บทบาทและหมวดหมู่ต่างๆ (ดึงตามที่คุณระบุ)
STAFF_ROLE_ID = 1538415866960412742

# แมปปิ้งหัวข้อกับบทบาทที่จะโดนแท็ก (Role IDs)
TICKET_OPTIONS = {
    "1": {
        "label": "1. ติดต่อทั่วไป/สอบถาม",
        "roles": [1538415866960412742]
    },
    "2": {
        "label": "2. แจ้งปัญหาผู้เล่น",
        "roles": [1538415808177508503]
    },
    "3": {
        "label": "3. แจ้งปัญหาแมพ/บัค",
        "roles": [1554112148995580056]
    },
    "4": {
        "label": "4. ติดต่อกองบัญชาการ",
        "roles": [1538415748106686554, 1538415746454130688]
    },
    "5": {
        "label": "5. ติดต่อคณะบริหาร",
        "roles": [1538415739411759176]
    },
    "6": {
        "label": "6. ติดต่อรัฐบาล",
        "roles": [1538415749859901511]
    },
    "7": {
        "label": "7. ติดต่อผู้พัฒนา",
        "roles": [1554112148995580056]
    }
}

# -------------------------------------------------------------
# 1. หน้าต่างกรอกเหตุผลในการเปิด Ticket (Modal)
# -------------------------------------------------------------
class TicketReasonModal(discord.ui.Modal):
    def __init__(self, category_key: str):
        super().__init__(title="แบบฟอร์มการแจ้งเรื่อง")
        self.category_key = category_key

        self.reason = discord.ui.TextInput(
            label="เหตุผลที่มาติดต่อ",
            style=discord.TextStyle.paragraph,
            placeholder="กรอกรายละเอียดหรือเหตุผลของคุณที่นี่...",
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        option_data = TICKET_OPTIONS[self.category_key]

        # สร้าง Overwrites (การกำหนดสิทธิ์ในห้อง)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # ให้สิทธิ์ทุก Role ที่เกี่ยวข้องในหัวข้อนั้นมองเห็นห้องได้
        for role_id in option_data["roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # ให้สิทธิ์บทบาทแอดมิน/สตาฟหลักเพิ่มความชัวร์
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # สร้างห้อง Ticket ใหม่
        channel_name = f"ticket-{user.name}".lower()
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Ticket created by {user.name}"
        )

        # ตอบกลับผู้ใช้ว่าสร้างห้องสำเร็จแล้ว
        await interaction.response.send_message(f"✅ สร้างตั๋วของคุณเรียบร้อยแล้ว: {ticket_channel.mention}", ephemeral=True)

        # ดึงข้อความแท็กบทบาท
        mentions_str = " ".join([f"<@&{rid}>" for rid in option_data["roles"]])

        # สร้างข้อความ Embed ในห้อง Ticket
        embed = discord.Embed(
            title=f"🎫 {option_data['label']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="👤 ผู้ติดต่อ", value=user.mention, inline=False)
        embed.add_field(name="📝 เหตุผลที่ติดต่อ", value=self.reason.value, inline=False)
        embed.set_footer(text="กรุณารอทีมงานตอบกลับสักครู่")

        # ส่งข้อความ Embed + แท็ก + ปุ่มจัดการ Ticket
        await ticket_channel.send(
            content=f"{user.mention} {mentions_str}",
            embed=embed,
            view=TicketControlView()
        )


# -------------------------------------------------------------
# 2. เมนู Dropdown สำหรับเลือกหัวข้อการติดต่อ
# -------------------------------------------------------------
class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=data["label"], value=key)
            for key, data in TICKET_OPTIONS.items()
        ]
        super().__init__(placeholder="เลือกหัวข้อที่ต้องการติดต่อ...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # เด้ง หน้าต่าง Pop-up (Modal) ให้กรอกเหตุผล
        await interaction.response.send_modal(TicketReasonModal(self.values[0]))


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())


# -------------------------------------------------------------
# 3. ปุ่มกดสร้าง Ticket หน้าแรก (ปุ่มสีเขียว)
# -------------------------------------------------------------
class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="กดเพื่อสร้าง Ticket", style=discord.ButtonStyle.success, custom_id="create_ticket_btn")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # เมื่อกดปุ่ม ให้แสดง Dropdown ให้เลือกว่าจะติดต่อเรื่องอะไร
        await interaction.response.send_message("กรุณาเลือกหัวข้อที่คุณต้องการติดต่อ:", view=TicketSelectView(), ephemeral=True)


# -------------------------------------------------------------
# 4. ปุ่มควบคุมภายในห้อง Ticket (รับตั๋ว / ปิด Ticket)
# -------------------------------------------------------------
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="รับตั๋ว", style=discord.ButtonStyle.success, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรวจสอบว่าผู้กดมี Role STAFF_ROLE_ID หรือไม่
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานปุ่มนี้!", ephemeral=True)
            return

        button.disabled = True
        button.label = f"รับตั๋วแล้วโดย {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🟢 **{interaction.user.mention}** ได้ทำการรับตั๋วนี้แล้ว!")

    @discord.ui.button(label="ปิด Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรวจสอบสิทธิ์เฉพาะคนที่มี Role STAFF_ROLE_ID
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ เฉพาะผู้ที่มีสิทธิ์เท่านั้นที่สามารถปิด Ticket ได้!", ephemeral=True)
            return

        await interaction.response.send_message("🔒 กำลังปิดและลบห้อง Ticket นี้ในอีก 5 วินาที...")
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()


# -------------------------------------------------------------
# Event บอทพร้อมทำงาน & คำสั่งสร้างหน้าต่างตั๋ว
# -------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"ล็อกอินเข้าสู่ระบบในชื่อ {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)


# คำสั่ง Slash Command พิมพ์ /setup_ticket เพื่อปล่อยแผงควบคุม Ticket
@bot.tree.command(name="setup_ticket", description="ส่งข้อความสร้างตั๋ว (สำหรับแอดมิน)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Ticket",
        description="กดเพื่อเรียกเจ้าหน้าที่\n\n**⚠️ ห้ามกดเล่นเด็ดขาด**",
        color=discord.Color.red()
    )
    await interaction.channel.send(embed=embed, view=CreateTicketView())
    await interaction.response.send_message("สร้างเมนู Ticket เรียบร้อยแล้ว!", ephemeral=True)


# ใส่ Token บอทของคุณที่นี่
bot.run("YOUR_BOT_TOKEN_HERE")
