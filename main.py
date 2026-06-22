import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-7s] %(name)s: %(message)s",
)

import bot.discord_bot
import bot.handlers
from bot.discord_bot import bot
from config import DISCORD_TOKEN

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
