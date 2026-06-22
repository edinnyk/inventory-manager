import json
import logging
from datetime import date

import requests
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2.service_account import Credentials

from config import SHEET_ID, get_google_credentials
from sheets.schema import HEADERS

logger = logging.getLogger(__name__)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


def _get_authorized_session() -> requests.Session:
    creds = get_google_credentials()
    credentials = Credentials.from_service_account_info(creds, scopes=SCOPE)
    credentials.refresh(AuthRequest())
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {credentials.token}"})
    return session


def _get_worksheet():
    session = _get_authorized_session()
    resp = session.get(f"{API_BASE}/{SHEET_ID}")
    if resp.status_code != 200:
        raise RuntimeError(f"Sheets API error ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    logger.info("opened sheet: %s", data.get("properties", {}).get("title", "?"))
    return session, data


def _ensure_headers(session, sheet_data):
    range_ = f"'{sheet_data['properties']['title']}'!A1:F1"
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code == 200:
        existing = resp.json().get("values", [])
        if existing and existing[0] == HEADERS:
            return

    body = {
        "requests": [{
            "updateCells": {
                "rows": [{"values": [{"userEnteredValue": {"stringValue": h}} for h in HEADERS]}],
                "fields": "userEnteredValue",
                "start": {"sheetId": 0, "rowIndex": 0, "columnIndex": 0},
            }
        }]
    }
    resp = session.post(f"{API_BASE}/{SHEET_ID}:batchUpdate", json=body)
    if resp.status_code != 200:
        logger.warning("failed to set headers: %s", resp.text[:300])


def append_entry(item_name: str, category: str, quantity: int, notes: str = "", unit: str = "units"):
    session, sheet_data = _get_worksheet()
    _ensure_headers(session, sheet_data)
    today = date.today().isoformat()
    row = [item_name, category, str(quantity), today, notes, unit]
    range_ = f"'{sheet_data['properties']['title']}'!A:F"
    body = {"values": [row]}
    resp = session.post(f"{API_BASE}/{SHEET_ID}/values/{range_}:append", params={"valueInputOption": "USER_ENTERED"}, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"append failed ({resp.status_code}): {resp.text[:300]}")


def get_recent(n: int = 5):
    session, sheet_data = _get_worksheet()
    range_ = f"'{sheet_data['properties']['title']}'!A:F"
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"read failed ({resp.status_code}): {resp.text[:300]}")
    rows = resp.json().get("values", [])
    if len(rows) <= 1:
        return []
    return rows[-n:]
