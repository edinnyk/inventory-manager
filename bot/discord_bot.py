import discord
from discord import app_commands

from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        await tree.sync(guild=discord.Object(id=guild.id))
    print(f"Bot logged in as {bot.user} in {len(bot.guilds)} guild(s)")
