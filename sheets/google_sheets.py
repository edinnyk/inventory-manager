import logging
import re
from datetime import datetime

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


def _range(sheet_name: str, cols: str) -> str:
    if re.search(r"[^\w]", sheet_name):
        return f"'{sheet_name}'!{cols}"
    return f"{sheet_name}!{cols}"


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _tab_info(tab_name: str):
    session = _get_authorized_session()
    resp = session.get(f"{API_BASE}/{SHEET_ID}")
    if resp.status_code != 200:
        raise RuntimeError(f"Sheets API error ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    for sheet in data["sheets"]:
        if sheet["properties"]["title"] == tab_name:
            return session, sheet["properties"]["title"], sheet["properties"]["sheetId"]
    raise RuntimeError(f"Tab '{tab_name}' not found")


def _ensure_audit_headers(session, sheet_name):
    range_ = _range(sheet_name, "A1:D1")
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
        logger.warning("failed to set audit headers: %s", resp.text[:300])


def _last_data_row(session, sheet_name, column="B"):
    range_ = _range(sheet_name, f"{column}:{column}")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    values = resp.json().get("values", [])
    for i in range(len(values) - 1, -1, -1):
        if values[i] and str(values[i][0]).strip():
            return i + 2
    return 2


def log_entry(item: str, delta: str, notes: str):
    session, sheet_name, _ = _tab_info("Audit Log")
    _ensure_audit_headers(session, sheet_name)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    range_ = _range(sheet_name, "A:D")
    body = {"values": [[item, delta, now, notes]]}
    resp = session.post(
        f"{API_BASE}/{SHEET_ID}/values/{range_}:append",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"log append failed ({resp.status_code}): {resp.text[:300]}")


def get_log(product: str, n: int = 5) -> list[dict]:
    session, sheet_name, _ = _tab_info("Audit Log")
    range_ = _range(sheet_name, "A:D")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"log read failed ({resp.status_code}): {resp.text[:300]}")
    rows = resp.json().get("values", [])
    if len(rows) <= 1:
        return []
    matched = []
    for row in reversed(rows[1:]):
        if len(row) >= 1 and str(row[0]).strip().lower() == product.lower():
            padded = row + [""] * (4 - len(row))
            matched.append({
                "item": padded[0],
                "delta": padded[1],
                "date": padded[2],
                "notes": padded[3],
            })
    return matched[:n]


def find_product_row(product: str) -> int | None:
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, "B:B")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"read failed ({resp.status_code}): {resp.text[:300]}")
    values = resp.json().get("values", [])
    for i, row in enumerate(values):
        if row and str(row[0]).strip().lower() == product.lower():
            return i + 1
    return None


def find_variant_col(variant: str) -> str | None:
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, "E1:ZZ1")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"read failed ({resp.status_code}): {resp.text[:300]}")
    headers = resp.json().get("values", [[]])[0]
    for i, val in enumerate(headers):
        if str(val).strip().lower() == variant.lower():
            return _col_letter(5 + i)
    return None


def list_variants() -> list[str]:
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, "E1:ZZ1")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    if resp.status_code != 200:
        raise RuntimeError(f"read failed ({resp.status_code}): {resp.text[:300]}")
    return [str(v).strip() for v in resp.json().get("values", [[]])[0] if str(v).strip()]


def matrix_read_cell(product: str, variant: str) -> int:
    row = find_product_row(product)
    col = find_variant_col(variant)
    if row is None:
        raise ValueError(f"Product '{product}' not found")
    if col is None:
        raise ValueError(f"Variant '{variant}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"{col}{row}")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    raw = resp.json().get("values", [[None]])[0][0]
    if raw is None or str(raw).strip() == "":
        return 0
    return int(float(str(raw).replace(",", "").replace("$", "")))


def matrix_write_cell(product: str, variant: str, value: int):
    row = find_product_row(product)
    col = find_variant_col(variant)
    if row is None:
        raise ValueError(f"Product '{product}' not found")
    if col is None:
        raise ValueError(f"Variant '{variant}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"{col}{row}")
    body = {"values": [[str(value)]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"write failed ({resp.status_code}): {resp.text[:300]}")


def matrix_get(product: str) -> dict[str, int]:
    row = find_product_row(product)
    if row is None:
        raise ValueError(f"Product '{product}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"E{row}:ZZ{row}")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    values = resp.json().get("values", [[]])[0]
    variants = list_variants()
    result = {}
    for i, var in enumerate(variants):
        if i < len(values):
            raw = values[i]
            if raw and str(raw).strip():
                result[var] = int(float(str(raw).replace(",", "").replace("$", "")))
            else:
                result[var] = 0
        else:
            result[var] = 0
    return result


def add_product_row(product: str, size: str = ""):
    session, sheet_name, _ = _tab_info("Inventory")
    next_row = _last_data_row(session, sheet_name, "B")
    range_ = _range(sheet_name, f"B{next_row}:C{next_row}")
    body = {"values": [[product, size]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"add product failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("added product row %s at row %d", product, next_row)


def add_variant_column(name: str):
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, "E1:ZZ1")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    existing = resp.json().get("values", [[]])[0]
    for val in existing:
        if str(val).strip().lower() == name.lower():
            raise ValueError(f"Variant '{name}' already exists")
    next_col = 5 + len(existing)
    col_letter = _col_letter(next_col)
    range_ = _range(sheet_name, f"{col_letter}1")
    body = {"values": [[name]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"add variant failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("added variant column %s at %s", name, col_letter)


def rename_variant_column(old: str, new: str):
    col = find_variant_col(old)
    if col is None:
        raise ValueError(f"Variant '{old}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"{col}1")
    body = {"values": [[new]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"rename variant failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("renamed variant %s to %s", old, new)
