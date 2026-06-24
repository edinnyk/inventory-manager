import json
import os
import re
import zoneinfo
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

SHEET_ID = os.getenv("SHEET_ID", "").strip()
if not SHEET_ID:
    raise ValueError("SHEET_ID is not set")

# Handle full Google Sheets URL instead of just the ID
m = re.search(r"/d/([a-zA-Z0-9_-]+)", SHEET_ID)
if m:
    SHEET_ID = m.group(1)

TIMEZONE_NAME = os.getenv("TIMEZONE", "Pacific/Honolulu")
TIMEZONE = zoneinfo.ZoneInfo(TIMEZONE_NAME)

_google_creds_cache: dict | None = None


def get_google_credentials() -> dict:
    global _google_creds_cache
    if _google_creds_cache is not None:
        return _google_creds_cache

    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip().strip("'\"")

    if not raw:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")

    if raw.startswith("{"):
        _google_creds_cache = json.loads(raw)
        return _google_creds_cache

    path = Path(raw)
    if path.exists():
        with open(path) as f:
            _google_creds_cache = json.load(f)
            return _google_creds_cache

    raise ValueError(
        "GOOGLE_SERVICE_ACCOUNT_JSON is neither valid JSON nor an existing file path"
    )
