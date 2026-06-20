from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SHEET_ID
from sheets.schema import HEADERS

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _get_worksheet():
    credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=SCOPE)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SHEET_ID)
    return sheet.sheet1


def _ensure_headers(worksheet):
    existing = worksheet.get_all_values()
    if existing and existing[0] == HEADERS:
        return
    worksheet.clear()
    worksheet.append_row(HEADERS)
    worksheet.format("A1:F1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})
    worksheet.freeze("1")


def append_entry(item_name: str, category: str, quantity: int, notes: str = "", unit: str = "units"):
    worksheet = _get_worksheet()
    _ensure_headers(worksheet)
    today = date.today().isoformat()
    row = [item_name, category, quantity, today, notes, unit]
    worksheet.append_row(row)


def get_recent(n: int = 5):
    worksheet = _get_worksheet()
    all_rows = worksheet.get_all_values()
    if len(all_rows) <= 1:
        return []
    data_rows = all_rows[1:]
    return data_rows[-n:]
