import json
import os

import discord
from discord import app_commands
from discord.ext import commands

# ===== НАСТРОЙКИ =====
TOKEN = os.getenv("DISCORD_TOKEN")  # токен бота берём из переменной окружения
WELCOME_CHANNEL = "общий"           # название канала для приветствий
AUTO_ROLE = "Участник"              # роль, которую получает каждый новичок
REACTION_ROLES = {                  # эмодзи -> название роли
    "🎮": "Геймер",
    "🎵": "Меломан",
    "🎨": "Художник",
}
PANEL_FILE = "panel.json"           # тут хранится id сообщения с ролями
# =====================

intents = discord.Intents.default()
intents.members = True  # нужно, чтобы видеть вход новых участников
bot = commands.Bot(command_prefix="!", intents=intents)


def load_panel_id():
    try:
        with open(PANEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("message_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_panel_id(message_id):
    with open(PANEL_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)


@bot.event
async def setup_hook():
    await bot.tree.sync()  # регистрируем слэш-команды


@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    # 1. Выдаём роль новичку
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE)
    if role:
        try:
            await member.add_roles(role, reason="Авто-роль")
        except discord.Forbidden:
            print("Нет прав выдать авто-роль: поднимите роль бота выше в списке")

    # 2. Отправляем приветствие
    channel = (
        discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
        or member.guild.system_channel
    )
    if channel:
        embed = discord.Embed(
            title="Добро пожаловать! 👋",
            description=f"{member.mention}, рады видеть тебя на сервере **{member.guild.name}**!",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Участник №{member.guild.member_count}")
        await channel.send(embed=embed)


@bot.tree.command(name="panel", description="Создать сообщение для выбора ролей")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    lines = [f"{emoji} — **{role}**" for emoji, role in REACTION_ROLES.items()]
    embed = discord.Embed(
        title="Выбери свои роли",
        description="Нажми на реакцию, чтобы получить роль. Убери реакцию — роль пропадёт.\n\n"
        + "\n".join(lines),
        color=discord.Color.blurple(),
    )
    await interaction.response.send_message("Панель создана!", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    for emoji in REACTION_ROLES:
        await message.add_reaction(emoji)
    save_panel_id(message.id)


async def toggle_role(payload: discord.RawReactionActionEvent, add: bool):
    if payload.message_id != load_panel_id():
        return
    role_name = REACTION_ROLES.get(str(payload.emoji))
    if not role_name:
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = discord.utils.get(guild.roles, name=role_name)
    if not member or member.bot or not role:
        return
    try:
        if add:
            await member.add_roles(role, reason="Реакция-роль")
        else:
            await member.remove_roles(role, reason="Реакция-роль")
    except discord.Forbidden:
        print(f"Нет прав управлять ролью {role_name}")


@bot.event
async def on_raw_reaction_add(payload):
    await toggle_role(payload, True)


@bot.event
async def on_raw_reaction_remove(payload):
    await toggle_role(payload, False)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Укажи токен: переменная окружения DISCORD_TOKEN")
    bot.run(TOKEN)
