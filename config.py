import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

SHEET_ID = os.getenv("SHEET_ID")
if not SHEET_ID:
    raise ValueError("SHEET_ID is not set")

_google_creds_cache: dict | None = None


def get_google_credentials() -> dict:
    global _google_creds_cache
    if _google_creds_cache is not None:
        return _google_creds_cache

    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
