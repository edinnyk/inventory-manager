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
            cmds = await tree.sync(guild=discord.Object(id=guild.id))
            names = [c.name for c in cmds]
            logger.info(
                "synced %d commands to guild %s: %s",
                len(cmds), guild.id, names,
            )
            if not cmds:
                logger.warning("guild sync returned 0 commands, trying global sync...")
                global_cmds = await tree.sync()
                logger.info(
                    "global sync returned %d commands: %s",
                    len(global_cmds), [c.name for c in global_cmds],
                )
        logger.info("Bot logged in as %s in %d guild(s)", bot.user, len(bot.guilds))
    except Exception as e:
        logger.error("on_ready error: %s", e)
