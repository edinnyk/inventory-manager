import bot.discord_bot
import bot.handlers
from bot.discord_bot import bot
from config import DISCORD_TOKEN

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
