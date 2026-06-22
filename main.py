import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-7s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Startup diagnostics (wrapped so bot always starts)
try:
    logger.info("--- Startup Diagnostics ---")
    logger.info("Python version: %s", sys.version)

    from config import DISCORD_TOKEN, SHEET_ID, get_google_credentials

    logger.info("DISCORD_TOKEN: set (len=%d)", len(DISCORD_TOKEN))
    logger.info("SHEET_ID: %s", SHEET_ID)

    try:
        creds = get_google_credentials()
        logger.info("GOOGLE creds: loaded, client_email=%s", creds.get("client_email", "MISSING"))
        logger.info("GOOGLE creds: project_id=%s", creds.get("project_id", "MISSING"))
        logger.info("GOOGLE creds: private_key length=%d", len(creds.get("private_key", "")))
    except Exception as e:
        logger.error("GOOGLE creds: FAILED - %s", e)
        creds = None

    if creds:
        try:
            from google.oauth2.service_account import Credentials
            import gspread

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            gc = gspread.authorize(Credentials.from_service_account_info(creds, scopes=scopes))
            logger.info("SHEETS auth: authorized successfully")

            sheet = gc.open_by_key(SHEET_ID)
            logger.info("SHEETS open_by_key: SUCCESS - title=%s", sheet.title)
        except gspread.exceptions.APIError as e:
            logger.error("SHEETS API error: %s", str(e)[:500])
        except Exception as e:
            logger.error("SHEETS unexpected error: %s", e)

    logger.info("--- End Diagnostics ---")
except Exception as e:
    logger.error("Startup diagnostic error: %s", e)

# Start the bot
import bot.discord_bot
import bot.handlers
from bot.discord_bot import bot
from config import DISCORD_TOKEN

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
