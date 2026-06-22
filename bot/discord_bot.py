import logging

import discord
from discord import app_commands

from config import DISCORD_TOKEN

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    try:
        logger.info("bot ready, syncing commands...")
        for guild in bot.guilds:
            await tree.sync(guild=discord.Object(id=guild.id))
            logger.info("synced commands to guild %s", guild.id)
        logger.info("Bot logged in as %s in %d guild(s)", bot.user, len(bot.guilds))
    except Exception as e:
        logger.error("on_ready error: %s", e)
