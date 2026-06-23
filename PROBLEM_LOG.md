# Problem Log

A chronological log of every issue encountered, its cause, and how it was resolved (or status if unresolved).

---

## P1 — gspread library returns HTML error pages

**Date:** Session 1
**Status:** Resolved

**Symptoms:** Bot running on Railway calls `gspread` to authenticate and read/write the sheet, but the library returns raw HTML "Page Not Found" pages instead of proper JSON API responses.

**Root Cause:** Unknown. `gspread`'s underlying HTTP client (`urllib3`/`requests`) was receiving non-JSON responses from the Google API. Possibly related to how Railway's runtime or Python version handled SSL/TLS or redirects. Could not be reproduced locally.

**Fix:** Replaced `gspread` entirely with direct HTTP calls using `requests` + `google-auth`. All Google Sheets API calls now go through `requests.Session` with a manually refreshed Bearer token.

**Files changed:** `sheets/google_sheets.py` (full rewrite), `requirements.txt` (removed `gspread`)

---

## P2 — Google service account JSON fails to parse

**Date:** Session 1
**Status:** Resolved

**Symptoms:** Bot starts but cannot authenticate with Google. Error: "GOOGLE_SERVICE_ACCOUNT_JSON is neither valid JSON nor an existing file path."

**Root Cause:** Two issues:
1. Railway wraps env vars in quotes when pasting multi-line JSON → `"'{...}'"` is not valid JSON
2. The original code only loaded from a file path, but Railway variables contain the raw JSON string directly

**Fix:** Added `.strip().strip("'\"")` to remove surrounding quotes. Added JSON string detection (starts with `{`) separate from file path detection. Added lazy caching via `_google_creds_cache` so the bot starts even if credentials fail (error surfaces at command time).

**Files changed:** `config.py`

---

## P3 — SHEET_ID is a full Google Sheets URL instead of bare ID

**Date:** Session 1
**Status:** Resolved

**Symptoms:** API returns 400 errors. SHEET_ID is set to `https://docs.google.com/spreadsheets/d/.../edit` instead of just the ID string.

**Root Cause:** Users copy-paste the full URL from the browser address bar.

**Fix:** Added regex extraction in `config.py`: `re.search(r"/d/([a-zA-Z0-9_-]+)", SHEET_ID)`. If a URL is detected, the ID is extracted automatically. Also added `.strip()` to handle whitespace.

**Files changed:** `config.py`

---

## P4 — "Unable to parse range" 400 error on append

**Date:** Session 1
**Status:** Resolved

**Symptoms:** Every call to append a row fails with `400 INVALID_ARGUMENT: Unable to parse range: 'Inventory Manager'!A:F`.

**Root Cause:** The code used `sheet_data['properties']['title']` which returns the SPREADSHEET title ("Inventory Manager"), not the SHEET TAB name (default "Sheet1"). Google Sheets API range syntax requires the tab name, not the spreadsheet name.

**Fix:** Changed to `data["sheets"][0]["properties"]["title"]` which accesses the first sheet tab's actual title. Added a `_range()` helper that wraps the name in single quotes only if it contains non-word characters (spaces, punctuation).

**Files changed:** `sheets/google_sheets.py`

---

## P5 — No git credential helper in WSL environment

**Date:** Session 1
**Status:** Unresolved (workaround)

**Symptoms:** `git push` fails with "could not read Username for 'https://github.com': No such device or address."

**Root Cause:** The code editor environment (WSL) doesn't have interactive git credentials configured. No GitHub token in environment variables.

**Workaround:** User must run `git push` from Windows Command Prompt or VS Code terminal on the host machine, where Windows git credential manager is available.

---

## P6 — Item names with digits fail to parse

**Date:** Session 1
**Status:** Resolved

**Symptoms:** Items like "USB-C 3m cable" or "5mm screw" cannot be entered because the parser rejects digits in item names.

**Root Cause:** Regex `QTY_PATTERN` used `[a-zA-Z][a-zA-Z\s-]*` which explicitly excluded digits.

**Fix:** Changed character class to `[a-zA-Z0-9\s.-]` to allow digits, periods, and hyphens in item names.

**Files changed:** `parser/extractor.py` (file later removed in v2)

---

## P7 — Railway deploy shows old code despite git push

**Date:** Session 2
**Status:** Unresolved

**Symptoms:** After `git push` (confirmed commits `504ea6c` and `de879f2` on `origin/main`), Railway continues running old v1 code. Old commands (`/diag`, `/inv`) still work. New v2 commands (`/add`, `/stock`, etc.) do not appear.

**Root Cause:** Unknown. Multiple attempts failed:
- Railway "Redeploy" button — runs old cached build
- Railway "New Deployment" → "Deploy from GitHub" — still runs old code
- Railway "Disconnect and reconnect repo" — still runs old code
- Pushing empty commit to trigger webhook — still runs old code
- Build logs show v2 dependencies installed correctly → image is BUILT with new code
- Deploy logs show "synced commands" → container IS running new code
- But Discord client never shows the new commands

**Hypothesis A:** The `tree.sync()` call returns success but sends an empty command list, clearing the guild's commands. This would mean the command tree was empty at sync time despite `handlers.py` importing successfully. Could be a race condition in discord.py 2.7.1.

**Hypothesis B:** Discord's client-side command cache is stale and not refreshing. Server-side commands ARE registered, but the desktop client doesn't show them. Web Discord or mobile might work.

**Hypothesis C:** Another instance of the bot (old container) is still running and its `on_ready` sync overwrites the new commands. This would require Railway to have two containers running simultaneously.

**Attempted fixes that didn't work:**
- Disconnect/reconnect GitHub repo in Railway Settings
- Click "New Deployment" instead of "Redeploy"
- Empty commit (`git commit --allow-empty -m "force rebuild"`)
- Full Discord client restart

**Next steps planned (not yet attempted):**
- Add logging to capture number of commands synced
- Add global sync fallback if guild sync returns 0
- Add `/version` command to verify deployed commit

**Relevant files:**
- `bot/discord_bot.py` — `on_ready()` sync logic
- `bot/handlers.py` — command registration via `@tree.command()`
- `main.py` — import order

---

## P8 — Audit tab headers write to wrong sheetId

**Date:** Session 2 (fixed before deploy)
**Status:** Resolved

**Symptoms:** `_ensure_audit_headers()` used hardcoded `sheetId: 0` when writing header rows via `batchUpdate`. Sheet ID 0 is always the FIRST tab (Inventory), not the Audit Log tab.

**Root Cause:** Hardcoded sheet ID instead of using the correct one from `_tab_info()`.

**Fix:** Updated `_ensure_audit_headers()` to accept `sheet_id` parameter. Updated `log_entry()` to pass the correct ID from `_tab_info("Audit Log")`.

**Files changed:** `sheets/google_sheets.py`

---

## P9 — Audit Log tab not auto-created

**Date:** Session 2 (fixed before deploy)
**Status:** Resolved

**Symptoms:** User creates the sheet with only an "Inventory" tab. The bot tries to write to "Audit Log" tab which doesn't exist, causing errors.

**Root Cause:** `_tab_info("Audit Log")` raised `RuntimeError` when tab didn't exist.

**Fix:** Added `auto_create=True` parameter to `_tab_info()`. When set, the function creates the tab via `batchUpdate` before returning. `log_entry()` and `get_log()` both use `auto_create=True`.

**Files changed:** `sheets/google_sheets.py`

---

## P10 — Parser regex captures too much in greedy mode

**Date:** Session 2 (fixed before deploy)
**Status:** Resolved

**Symptoms:** Input `"3 maple 5 cherry"` returned `[("maple 5 cherry", 3)]` — the second quantity and variant were consumed as part of the first variant name.

**Root Cause:** The `var1` capture group used `[a-zA-Z0-9\s/&-]*` which included digits. The greedy quantifier `*` consumed everything including "5 cherry".

**Fix:** Removed `0-9` from the character class. Variant names are now limited to `[a-zA-Z][a-zA-Z\s/&-]*` (letters, spaces, slashes, hyphens, ampersands — no digits).

**Files changed:** `parser/pairs.py`

**Tested formats (all pass):**
```
3 maple 5 cherry            → [("maple", 3), ("cherry", 5)]
maple 3 cherry 5            → [("maple", 3), ("cherry", 5)]
maple:3 cherry:5            → [("maple", 3), ("cherry", 5)]
3x maple 5x cherry          → [("maple", 3), ("cherry", 5)]
3 maple, 5 cherry           → [("maple", 3), ("cherry", 5)]
3 maple and 5 cherry        → [("maple", 3), ("cherry", 5)]
maple:3, 5 cherry and 2x OAK → [("maple", 3), ("cherry", 5), ("OAK", 2)]
3 hard maple 5 cherry       → [("hard maple", 3), ("cherry", 5)]
```

---

## Legacy Problem Summary

| ID | Problem | Status | Fix |
|----|---------|--------|-----|
| P1 | gspread returns HTML | Resolved | Direct `requests` API calls |
| P2 | Credentials parse failure | Resolved | Quote stripping + lazy loading |
| P3 | Full URL as SHEET_ID | Resolved | Regex extraction |
| P4 | Wrong sheet tab name | Resolved | `data["sheets"][0]["properties"]["title"]` |
| P5 | No git auth in WSL | Workaround | Push from Windows |
| P6 | Digits in item names | Resolved | Regex char class fix |
| P7 | Railway deploys old code | **UNRESOLVED** | See hypothesis A/B/C above |
| P8 | Wrong sheetId in headers | Resolved | Pass correct sheet_id |
| P9 | Audit tab not created | Resolved | Auto-create option |
| P10 | Greedy parser regex | Resolved | Remove digits from variant char class |
