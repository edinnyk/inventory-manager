import logging
import re
from datetime import datetime

import requests
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2.service_account import Credentials

from config import SHEET_ID, TIMEZONE, get_google_credentials
from sheets.schema import HEADERS, NON_VARIANT_HEADERS

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


def _cap(s: str) -> str:
    return s.strip().upper()


def _tab_info(tab_name: str, auto_create: bool = False):
    session = _get_authorized_session()
    resp = session.get(f"{API_BASE}/{SHEET_ID}")
    if resp.status_code != 200:
        raise RuntimeError(f"Sheets API error ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    for sheet in data["sheets"]:
        if sheet["properties"]["title"] == tab_name:
            return session, sheet["properties"]["title"], sheet["properties"]["sheetId"]
    if not auto_create:
        raise RuntimeError(f"Tab '{tab_name}' not found")
    body = {"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
    resp = session.post(f"{API_BASE}/{SHEET_ID}:batchUpdate", json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"create tab failed ({resp.status_code}): {resp.text[:300]}")
    new_id = resp.json()["replies"][0]["addSheet"]["properties"]["sheetId"]
    logger.info("created tab '%s' (sheetId=%s)", tab_name, new_id)
    return session, tab_name, new_id


def _ensure_audit_headers(session, sheet_name, sheet_id):
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
                "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0},
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


def _variant_headers(session, sheet_name):
    range_ = _range(sheet_name, "E1:ZZ1")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    headers = resp.json().get("values", [[]])[0]
    variants = []
    for i, h in enumerate(headers):
        name = str(h).strip()
        if name and name.lower() not in NON_VARIANT_HEADERS:
            variants.append((name, _col_letter(5 + i)))
    return variants


def log_entry(item: str, delta: str, notes: str):
    session, sheet_name, sheet_id = _tab_info("Audit Log", auto_create=True)
    _ensure_audit_headers(session, sheet_name, sheet_id)
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")
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
    session, sheet_name, _ = _tab_info("Audit Log", auto_create=True)
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
    for name, col in _variant_headers(session, sheet_name):
        if name.lower() == variant.lower():
            return col
    return None


def list_variants() -> list[str]:
    session, sheet_name, _ = _tab_info("Inventory")
    return [name for name, _ in _variant_headers(session, sheet_name)]


def _to_int(raw) -> int:
    if raw is None:
        return 0
    s = str(raw).strip()
    if not s:
        return 0
    s = s.replace(",", "").replace("$", "")
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


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
    return _to_int(raw)


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
    variants = _variant_headers(session, sheet_name)
    if not variants:
        return {}
    first_col = variants[0][1]
    last_col = variants[-1][1]
    range_ = _range(sheet_name, f"{first_col}{row}:{last_col}{row}")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    values = resp.json().get("values", [[]])[0]
    result = {}
    for i, (name, _) in enumerate(variants):
        raw = values[i] if i < len(values) else None
        result[name] = _to_int(raw)
    return result


def product_info(product: str) -> dict:
    row = find_product_row(product)
    if row is None:
        raise ValueError(f"Product '{product}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"B{row}:D{row}")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    vals = resp.json().get("values", [[None, None, None]])[0]
    return {
        "product": str(vals[0]).strip() if len(vals) > 0 and vals[0] else "",
        "size": str(vals[1]).strip() if len(vals) > 1 and vals[1] else "",
        "carcass": str(vals[2]).strip() if len(vals) > 2 and vals[2] else "",
    }


def add_product_row(product: str, size: str = ""):
    session, sheet_name, _ = _tab_info("Inventory")
    next_row = _last_data_row(session, sheet_name, "B")
    range_ = _range(sheet_name, f"B{next_row}:C{next_row}")
    body = {"values": [[_cap(product), _cap(size)]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"add product failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("added product row %s at row %d", _cap(product), next_row)


def add_variant_column(name: str):
    session, sheet_name, _ = _tab_info("Inventory")
    variants = _variant_headers(session, sheet_name)
    capped = _cap(name)
    for vname, _ in variants:
        if vname.lower() == capped.lower():
            raise ValueError(f"Variant '{capped}' already exists")
    # Find the last non-empty column in row 1
    range_ = _range(sheet_name, "A1:ZZ1")
    resp = session.get(f"{API_BASE}/{SHEET_ID}/values/{range_}")
    headers = resp.json().get("values", [[]])[0]
    last_non_empty = 0
    for i, h in enumerate(headers):
        if str(h).strip():
            last_non_empty = i + 1
    next_col = last_non_empty + 1
    col_letter = _col_letter(next_col)
    range_ = _range(sheet_name, f"{col_letter}1")
    body = {"values": [[capped]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"add variant failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("added variant column %s at %s", capped, col_letter)


def rename_variant_column(old: str, new: str):
    col = find_variant_col(old)
    if col is None:
        raise ValueError(f"Variant '{old}' not found")
    session, sheet_name, _ = _tab_info("Inventory")
    range_ = _range(sheet_name, f"{col}1")
    body = {"values": [[_cap(new)]]}
    resp = session.put(
        f"{API_BASE}/{SHEET_ID}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"rename variant failed ({resp.status_code}): {resp.text[:300]}")
    logger.info("renamed variant %s to %s", old, _cap(new))
