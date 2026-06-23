import json
import logging
import re
from datetime import date

import requests
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2.service_account import Credentials

from config import SHEET_ID, get_google_credentials
from sheets.schema import CATEGORIES_HEADERS, HEADERS

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


def _get_spreadsheet():
    session = _get_authorized_session()
    resp = session.get(f"{API_BASE}/{SHEET_ID}")
    if resp.status_code != 200:
        raise RuntimeError(f"Sheets API error ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    sheet_name = data["sheets"][0]["properties"]["title"]
    logger.info("opened sheet: %s tab: %s", data.get("properties", {}).get("title", "?"), sheet_name)
    return session, sheet_name


def _range(sheet_name: str, cols: str) -> str:
    if re.search(r"[^\w]", sheet_name):
        return f"'{sheet_name}'!{cols}"
    return f"{sheet_name}!{cols}"


def _ensure_headers(session, sheet_name):
    range_ = _range(sheet_name, f"A1:{chr(64 + len(HEADERS))}1")
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


def append_entry(item_name: str, category: str, quantity: int, subcategory: str = "", notes: str = "", unit: str = "units"):
    session, sheet_name = _get_spreadsheet()
    _ensure_headers(session, sheet_name)
    today = date.today().isoformat()
    row = [item_name, category, subcategory, str(quantity), today, notes, unit]
    range_ = _range(sheet_name, "A:G")
    body = {"values": [row]}
    resp = session.post(f"{API_BASE}/{SHEET_ID}/values/{range_}:append", params={"valueInputOption": "USER_ENTERED"}, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"append failed ({resp.status_code}): {resp.text[:300]}")


def get_recent(n: int = 5):
    session, sheet_name = _get_spreadsheet()
    range_ = _range(sheet_name, "A:G")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"read failed ({resp.status_code}): {resp.text[:300]}")
    rows = resp.json().get("values", [])
    if len(rows) <= 1:
        return []
    return rows[-n:]


def _get_or_create_tab(session, tab_name: str):
    resp = session.get(f"{API_BASE}/{SHEET_ID}")
    if resp.status_code != 200:
        raise RuntimeError(f"Sheets API error ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    for sheet in data.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            return sheet["properties"]["sheetId"]

    body = {
        "requests": [{
            "addSheet": {
                "properties": {"title": tab_name}
            }
        }]
    }
    resp = session.post(f"{API_BASE}/{SHEET_ID}:batchUpdate", json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"create tab failed ({resp.status_code}): {resp.text[:300]}")
    new_id = resp.json()["replies"][0]["addSheet"]["properties"]["sheetId"]
    return new_id


def sync_categories_tab(category_keywords: dict[str, list[str]], subcategory_data: dict[str, dict[str, list[str]]]):
    session = _get_authorized_session()
    tab_id = _get_or_create_tab(session, "Categories")

    rows = [CATEGORIES_HEADERS]
    for cat in sorted(category_keywords):
        top_kw = list(category_keywords[cat])
        subs = subcategory_data.get(cat, {})
        if subs:
            for subcat in sorted(subs):
                for kw in subs[subcat]:
                    try:
                        top_kw.remove(kw)
                    except ValueError:
                        pass
                rows.append([cat, subcat, ", ".join(sorted(subs[subcat]))])
        if top_kw:
            rows.append([cat, "", ", ".join(sorted(top_kw))])

    range_ = f"'Categories'!A1:{chr(64 + len(CATEGORIES_HEADERS))}{len(rows)}"
    body = {"values": rows}
    resp = session.put(f"{API_BASE}/{SHEET_ID}/values/{range_}", params={"valueInputOption": "USER_ENTERED"}, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"sync categories failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("synced %d rows to Categories tab", len(rows))
