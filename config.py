import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _load_google_credentials():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")

    path = Path(raw)
    if path.exists():
        with open(path) as f:
            return json.load(f)

    return json.loads(raw)


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

SHEET_ID = os.getenv("SHEET_ID")
if not SHEET_ID:
    raise ValueError("SHEET_ID is not set")

GOOGLE_CREDENTIALS = _load_google_credentials()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
