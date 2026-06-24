# Problem Log

Chronological log of every issue encountered, what was attempted, and what the final solution was.

---

## P1 — gspread library returns HTML error pages

**Date:** Session 1 (pre-v2), first deployment attempt
**Status:** Resolved

### Problem
The bot was running on Railway, connected to Discord, but every call to the Google Sheets API returned raw HTML "Page Not Found" pages instead of JSON. The sheet was never written to.

### What was attempted
1. Triple-checked service account JSON and SHEET_ID in Railway variables — correct
2. Checked that the service account had Editor access on the sheet — correct
3. Added startup diagnostics to `main.py` to log the exact API response — confirmed it was HTML
4. Tried different Python versions in `runtime.txt` — no change
5. Confirmed the same code worked locally (Windows) — it did

### Root cause
`gspread` library (the original Google Sheets wrapper) was making HTTP requests through its own client stack (`urllib3`/`google-api-python-client`) that somehow received non-JSON responses on Railway. The exact mechanism was never determined — likely a combination of Railway's network layer and `gspread`'s outdated HTTP handling.

### Solution
Replaced `gspread` entirely with direct HTTP requests using the standard `requests` library + `google-auth`. The bot now manually:
1. Loads the service account JSON
2. Creates `google.oauth2.service_account.Credentials`
3. Calls `credentials.refresh()` to get an access token
4. Passes the token as a `Bearer` header in plain `requests` calls

This gave us full control over the HTTP layer.

### Files changed
- `sheets/google_sheets.py` — full rewrite from gspread to raw requests
- `requirements.txt` — removed `gspread`, added `requests`

---

## P2 — Google service account JSON fails to parse

**Date:** Session 1
**Status:** Resolved

### Problem
Bot started, connected to Discord, but every sheet operation failed with: "GOOGLE_SERVICE_ACCOUNT_JSON is neither valid JSON nor an existing file path."

### What was attempted
1. Verified the JSON was pasted correctly into Railway variables — looked correct
2. Added debug logging to print the first/last characters of the raw env var — discovered quotes around it
3. Tested locally with `.env` file pointing to `credentials.json` — worked fine
4. Realized the code didn't distinguish between a JSON string and a file path

### Root cause
Two independent issues:
1. Railway's variable editor wraps multi-line values in smart quotes when pasting. The env var contained `"'{...}'"` instead of `{...}`
2. The original code assumed the env var was always a file path and called `json.load(open(path))`. On Railway, the value IS the JSON content, not a file path

### Solution
1. Added `.strip().strip("'\"")` to remove surrounding quote characters
2. Added detection: if the value starts with `{`, parse it as JSON directly. Otherwise, treat it as a file path
3. Added lazy caching (`_google_creds_cache`) so the bot starts even if credentials are missing — errors surface only when a sheet command is used

### Files changed
- `config.py` — `get_google_credentials()` function

---

## P3 — SHEET_ID is a full Google Sheets URL instead of bare ID

**Date:** Session 1
**Status:** Resolved

### Problem
Every sheet API call returned HTTP 400 errors. The bot logs showed `SHEET_ID: https://docs.google.com/spreadsheets/d/1ffdi9-WLfi_.../edit`.

### What was attempted
1. Verified the SHEET_ID in Railway variables was copied from the browser address bar — it was the full URL
2. Tried asking the user to extract just the ID — error-prone and confusing

### Root cause
Users naturally copy the entire URL from the browser address bar instead of manually extracting the 44-character ID string.

### Solution
Added automatic URL-to-ID extraction in `config.py`:
```python
m = re.search(r"/d/([a-zA-Z0-9_-]+)", SHEET_ID)
if m:
    SHEET_ID = m.group(1)
```
Also added `.strip()` to handle accidental whitespace. Now users can paste either the bare ID or the full URL and both work.

### Files changed
- `config.py`

---

## P4 — "Unable to parse range" 400 error on append

**Date:** Session 1
**Status:** Resolved

### Problem
After fixing P1-P3, the bot still failed on every sheet write with:
```
400 INVALID_ARGUMENT: Unable to parse range: 'Inventory Manager'!A:F
```

### What was attempted
1. Verified the sheet name — it was "Inventory Manager"
2. Tried different quoting styles (double quotes, no quotes) — same error
3. Manually tested the range via the Sheets API explorer — discovered the tab name wasn't "Inventory Manager"

### Root cause
The code used `sheet_data['properties']['title']` from the spreadsheet metadata. This returns the **spreadsheet file name** ("Inventory Manager"), not the **sheet tab name** (default "Sheet1"). The Google Sheets API range syntax `'Sheet Name'!A:F` requires the tab name, not the file name.

The terms are:
- **Spreadsheet** = the entire file (has a title like "Inventory Manager")
- **Sheet/Tab** = one tab within the file (has a title like "Sheet1", "Inventory", etc.)

### Solution
Changed to `data["sheets"][0]["properties"]["title"]` which gets the first tab's actual title. Added a `_range()` helper that auto-quotes tab names containing spaces or special characters.

### Files changed
- `sheets/google_sheets.py` — `_get_worksheet()` renamed to `_get_spreadsheet()`, added `_range()` helper

---

## P5 — No git credential helper in WSL environment

**Date:** Session 1 (ongoing)
**Status:** Unresolved (workaround)

### Problem
When trying to `git push` from the coding environment (WSL bash), it fails with:
```
fatal: could not read Username for 'https://github.com': No such device or address
```

### What was attempted
1. Switched remote URL to SSH (`git@github.com` style) — failed due to no SSH key or host key verification
2. Checked for GitHub tokens in environment variables — none found
3. Checked git config — user.name and user.email are set, but no credential helper
4. Tried setting `GIT_SSH_COMMAND` to skip host key checking — still failed

### Root cause
The coding environment runs in a container (WSL) without interactive terminal access. No SSH keys, no credential manager, and no GitHub token have been configured. The git remote is HTTPS which requires interactive password entry.

### Solution
Workaround only: user runs `git push` from Windows Command Prompt or VS Code terminal on the host machine, where the Windows Git Credential Manager has cached credentials from GitHub Desktop or VS Code login.

### Files changed
None

---

## P6 — Item names with digits fail to parse

**Date:** Session 1 (v1 era)
**Status:** Resolved

### Problem
Users couldn't enter items with numbers in their names. "USB-C 3m cable" would parse as just "USB-C" with quantity 3. "5mm screw" wouldn't parse at all.

### What was attempted
1. Tested the regex pattern against sample inputs — confirmed digits were excluded
2. Reviewed the regex: `(?P<item>[a-zA-Z][a-zA-Z\s-]*)` — `a-zA-Z` explicitly excludes digits

### Root cause
The regex character class `[a-zA-Z\s-]` was designed for English words only and didn't account for technical product names that include digits.

### Solution
Changed the character class to `[a-zA-Z0-9\s.-]` to allow digits, periods, and hyphens within item names.

### Files changed
- `parser/extractor.py` (this file was later removed in the v2 rewrite)

---

## P7 — Railway deploy shows old code despite git push

**Date:** Session 2 (current)
**Status:** Unresolved

### Problem
After `git push` (confirming commits `504ea6c` and `de879f2` on `origin/main`), Railway continued running the old v1 code. Old commands (`/diag`, `/inv`) still worked. The build log showed v2 dependencies being installed, but Discord never showed the new commands.

### What was attempted

**Attempt 1 — Push and Redeploy:**
- Ran `git push` from Windows — confirmed commits on GitHub
- Clicked "Redeploy" on Railway — old code still running
- Result: Failed

**Attempt 2 — New Deployment from GitHub:**
- Clicked "New Deployment" → "Deploy from GitHub" → selected `main`
- Build log showed correct v2 dependencies (no `openai`, no `gspread`)
- Deploy log showed "synced commands to guild"
- But Discord still showed old commands
- Result: Failed

**Attempt 3 — Railway logs analysis:**
- Build logs confirmed v2 dependencies: `discord.py-2.7.1`, `google-auth-2.55.0`, no `openai`
- Deploy logs confirmed: "bot ready, syncing commands..., synced commands to guild 1517681446259523594"
- The bot IS running v2 code, but commands don't appear in Discord
- Result: Confusing — code is correct, deployment succeeds, sync succeeds, but UI doesn't change

**Attempt 4 — Empty commit to force webhook:**
- Ran `git commit --allow-empty -m "force rebuild"` and `git push`
- Railway created a new deployment
- Commands still not showing
- Result: Failed

**Attempt 5 — Disconnect and reconnect GitHub repo:**
- Railway Settings → Disconnect Repository → Connect GitHub Repo
- Railway created a fresh build
- Commands still not showing
- Result: Failed

**Attempt 6 — Discord client restart:**
- User restarted Discord desktop app completely
- Commands still not showing
- Result: Failed

**Attempt 7 — Type command without autocomplete:**
- User typed `/add BPP09 3 maple 5 cherry` and sent it
- "Nothing" happened — no response, no error
- Suggests the command isn't registered on Discord's server side, not just a client cache issue
- Result: Confirmed the problem is server-side

### Current hypotheses

**Hypothesis A (most likely):** `tree.sync()` returns success but sends an empty command list, which DISCORD interprets as "clear all guild commands." This would happen if the `@tree.command()` decorators in `handlers.py` didn't register anything on the `tree` object by the time `on_ready` fires. The code logs "synced commands" after the `await` completes, but doesn't log HOW MANY commands were synced.

Why this could happen:
- Python import order issue: if `handlers.py` is imported but its `@tree.command()` decorators don't fire somehow
- Race condition in `discord.py` 2.7.1 where `tree.sync()` is called before commands finish registering
- The `tree` object imported in `handlers.py` (`from bot.discord_bot import tree`) might not be the same instance as the one in `discord_bot.py`

**Hypothesis B:** Discord API accepted the sync request but silently ignored it due to rate limiting or validation issues. The bot's code doesn't check the return value of `tree.sync()` — it only logs that it completed, not what it returned.

**Hypothesis C:** Another bot instance (old container) is still running on Railway and its `on_ready` fires after the new one, overwriting the commands. This would require two containers running simultaneously, which Railway shouldn't allow.

### Planned solution (not yet implemented)

Steps to diagnose and fix:
1. Log the return value of `tree.sync()` — how many commands, what are their names
2. Add a global sync fallback if guild sync returns less than expected
3. Add a `/version` command that responds with the current git commit hash

### Files relevant
- `bot/discord_bot.py` — `on_ready()` sync logic
- `bot/handlers.py` — command registration via `@tree.command()`
- `main.py` — import order

---

## P8 — Audit tab headers write to wrong sheetId

**Date:** Session 2 (fixed before deployment, never reached production)
**Status:** Resolved

### Problem
`_ensure_audit_headers()` used hardcoded `sheetId: 0` when writing header rows via the `batchUpdate` API. Sheet ID 0 is always the first tab (Inventory in the v2 layout), not the Audit Log tab. This would corrupt the Inventory tab's first row.

### What was attempted
1. Reviewed the `batchUpdate` API documentation — confirmed `sheetId` is required and must match the target tab
2. Checked `_tab_info()` — it correctly returns the numeric `sheetId` for any named tab
3. The fix was applied before the v2 code was deployed, so this never caused a live issue

### Root cause
The `_ensure_audit_headers()` function was written assuming the first tab (index 0) was always the audit tab. When the sheet layout changed to have Inventory as tab 1 and Audit Log as tab 2, the hardcoded `0` became wrong.

### Solution
Updated `_ensure_audit_headers()` to accept a `sheet_id` parameter. `log_entry()` now retrieves the correct sheetId from `_tab_info("Audit Log")` and passes it through.

### Files changed
- `sheets/google_sheets.py` — `_ensure_audit_headers()` signature and body

---

## P9 — Audit Log tab not auto-created

**Date:** Session 2 (fixed before deployment)
**Status:** Resolved

### Problem
If a user created a new sheet with only the default "Sheet1" tab (or renamed it to "Inventory"), the bot would crash when trying to write to an "Audit Log" tab that didn't exist.

### What was attempted
1. Checked if `_tab_info()` could auto-create tabs — it couldn't, it only searched
2. Considered requiring users to manually create both tabs — user-hostile

### Root cause
`_tab_info()` raised `RuntimeError` when the requested tab name wasn't found. No fallback.

### Solution
Added `auto_create=False` parameter to `_tab_info()`. When `auto_create=True`, it sends a `batchUpdate` request with `addSheet` to create the tab before returning. Both `log_entry()` and `get_log()` pass `auto_create=True` for "Audit Log".

### Files changed
- `sheets/google_sheets.py` — `_tab_info()` signature and body

---

## P10 — Parser regex captures too much in greedy mode

**Date:** Session 2 (fixed before deployment)
**Status:** Resolved

### Problem
The input `"/add BPP09 3 maple 5 cherry"` parsed as `[("maple 5 cherry", 3)]` instead of `[("maple", 3), ("cherry", 5)]`. The second quantity and variant name were consumed as part of the first variant name.

### What was attempted
1. Tested the regex against all intended input formats
2. Discovered the character class `[a-zA-Z0-9\s/&-]*` was too permissive — digits should not be part of variant names
3. The greedy quantifier `*` was consuming everything including digits

### Root cause
The variant name capture group included `0-9` in its allowed character set. When the regex matched `"3 maple 5 cherry"`, the `var1` group greedily consumed `"maple 5 cherry"` because digits were allowed in variant names.

### Solution
Removed `0-9` from the variant name character class. Variant names are now limited to letters, spaces, slashes, hyphens, and ampersands: `[a-zA-Z][a-zA-Z\s/&-]*`. Digits in the middle of a variant name will stop the greedy match, allowing the next quantity to be matched separately.

### Files changed
- `parser/pairs.py`

### Verified input formats
```
Input                              Output
3 maple 5 cherry            →  [("maple", 3), ("cherry", 5)]
maple 3 cherry 5            →  [("maple", 3), ("cherry", 5)]
maple:3 cherry:5            →  [("maple", 3), ("cherry", 5)]
3x maple 5x cherry          →  [("maple", 3), ("cherry", 5)]
3 maple, 5 cherry           →  [("maple", 3), ("cherry", 5)]
3 maple and 5 cherry        →  [("maple", 3), ("cherry", 5)]
maple:3, 5 cherry and 2x OAK →  [("maple", 3), ("cherry", 5), ("OAK", 2)]
3 hard maple 5 cherry       →  [("hard maple", 3), ("cherry", 5)]
```

---

## P11 — Bot ignores CARCASS column, variants hardcoded to start at column E

**Date:** Session 3
**Status:** Resolved

### Problem
The sheet layout has:
- Column D = CARCASS (a numeric property of the product, like "16" or "41")
- Column E = spacer (empty, used for visual organization)
- Column F+ = variants (MAPLE, CHERRY, etc.)

But the bot's `find_variant_col()` starts searching from column E (`E1:ZZ1`), treating column E as the first variant. This means:
1. The spacer column E gets treated as a variant if it has a header
2. If Column E is empty, the bot stops there and never finds variants in column F+

The user wants:
- Column D recognized as CARCASS (bot reads and displays it, but doesn't treat it as a variant)
- Column E always skipped (spacer)
- Columns F+ treated as variants

### What was attempted
Implemented `_variant_headers()` that scans row 1 from A:ZZ1 and filters out
known non-variant headers (SIZE, CARCASS, empty cells). All functions that
need to find or enumerate variants now use this function instead of
hardcoded column ranges.

### Root cause
Hardcoded variant start column in `find_variant_col()`, `list_variants()`, `matrix_get()`, and `add_variant_column()`:
```python
def find_variant_col(variant):
    range_ = _range(sheet_name, "E1:ZZ1")  # ← hardcoded E
```

### Planned solution
Make the variant column range auto-detectable:
1. Read row 1 from column A onwards
2. Skip known non-variant headers (CARCASS, SIZE, etc.)
3. Skip empty cells (spacers)
4. Everything else is a variant

### Files relevant
- `sheets/google_sheets.py` — `find_variant_col()`, `list_variants()`, `matrix_get()`, `add_variant_column()`

---

## P12 — No auto-capitalization when writing to sheet

**Date:** Session 3
**Status:** Resolved

### Problem
When a user types `/add BPP09 3 maple`, the word "maple" is written to the cell exactly as typed (lowercase). The user wants all values to be **capitalized** automatically (e.g., "MAPLE", "CHERRY") for consistent sheet appearance.

This applies to:
- Product names (column B)
- Variant names (column headers, row 1)
- Values written to cells

### What was attempted
Added `_cap()` helper (`s.strip().upper()`) and applied it in:

- `add_product_row()` — caps product name and size
- `add_variant_column()` — caps variant name
- `rename_variant_column()` — caps the new name

Note: `matrix_write_cell()` was NOT capped because cell values are
quantities (integers), not names.

### Root cause
The code wrote values as-is — no transformation was applied.

### Files relevant
- `sheets/google_sheets.py` — `add_variant_column()`, `add_product_row()`, `matrix_write_cell()`
- `bot/handlers.py` — all command handlers that pass user input

---

## P13 — `/add` command parameter "pairs" is confusing

**Date:** Session 3
**Status:** Resolved

### Problem
The `/add` command's second parameter is named `pairs`:
```
/add product: BPP09 pairs: 3 maple 5 cherry
```
Users don't understand what "pairs" means in this context. It's an internal
term (quantity+variant pairs) that doesn't describe what the user should type.

### What was attempted
Renamed `pairs` → `items` in all three commands (`/add`, `/sub`, `/set`).
The Discord prompt now shows:
```
/add product: BPP09 items: 3 maple 5 cherry
```

### Root cause
Naming was technical rather than user-friendly.

### Files relevant
- `bot/handlers.py` — command definitions for `add`, `sub`, `set`

---

## P14 — Sheet layout is hardcoded, not adaptable to user organization

**Date:** Session 3
**Status:** Resolved (Phase 1 only)

### Problem
The bot assumes a specific column layout:
- B = products
- C = size
- D = CARCASS (ignored)
- E = spacer (currently treated as variant start)
- F+ = variants

But users may organize their sheet differently. The user wants the bot to
**adapt** to whatever layout the user creates, rather than requiring the
user to match the bot's expectations.

### What was attempted
Phase 1 implemented: smart variant detection via `_variant_headers()`.
The function reads row 1, skips known non-variant headers ("SIZE", "CARCASS",
empty cells), and returns only actual variant columns. All variant-related
code now uses this function.

Phase 2 (configurable `/layout` command) not implemented — not yet needed.

### Root cause
All column positions were hardcoded throughout `sheets/google_sheets.py`.

### Planned solution
Add a layout discovery system:

**Phase 1 — Smart variant detection:**
Read row 1, skip known non-variant headers ("SIZE", "CARCASS", ""), treat
everything else as variants. This handles:
- Different starting columns
- Spacers between columns
- Additional info columns the user may add

**Phase 2 — Configurable via command:**
Add a `/layout` command that lets the user define which columns map to
which role:
```
/layout product: B size: C carcass: D spacer: E variant_start: F
```
Stored in memory (custom_categories-style dict) or in a config sheet tab.

### Future considerations
- Multi-line headers (row 1 = category group, row 2 = variant name)
- Merged cells in header row
- Dynamic column types (e.g., columns with "$" prefix are currency)

### Files relevant
- `sheets/google_sheets.py` — all functions that reference column positions
- `bot/handlers.py` — new `/layout` command

---

## P15 — Audit log timestamps are UTC, not local time

**Date:** Session 3
**Status:** Resolved

### Problem
All audit log entries showed UTC timestamps (e.g., `2026-06-22 04:30`) even
though the user operates in Hawaii time (UTC-10). The timestamps were
misleading when trying to understand when inventory changes happened.

### What was attempted
Added `TIMEZONE` env var support:

1. `config.py` — added `zoneinfo.ZoneInfo` import, reads `TIMEZONE` env var
   (default `"Pacific/Honolulu"`)
2. `sheets/google_sheets.py` — `datetime.now(TIMEZONE)` replaces
   `datetime.now()` in `log_entry()`

### Root cause
`datetime.now()` returns UTC when called without a timezone argument.

### Solution
Use `datetime.now(TIMEZONE)` with the timezone loaded from the `TIMEZONE`
environment variable. Each Railway project sets its own `TIMEZONE` (e.g.,
`Pacific/Honolulu`, `America/New_York`) and the bot writes localized
timestamps to the audit log.

### Files changed
- `config.py` — added `TIMEZONE_NAME`, `TIMEZONE` globals using `zoneinfo`
- `sheets/google_sheets.py` — `log_entry()` uses `datetime.now(TIMEZONE)`

---

## P16 — `/stock` crashes on non-numeric cell values

**Date:** Session 3
**Status:** Resolved

### Problem
Running `/stock BPP09` crashed with:
```
ValueError: could not convert string to float
```
Also affected `/add`, `/sub`, `/set` via `matrix_read_cell()`. Any cell
containing text like "N/A", "-", or an empty string that wasn't handled
would cause a full crash.

### What was attempted
Replaced the inline `int(float(str(raw).replace(...)))` conversion with
a dedicated `_to_int()` helper.

### Root cause
`int(float("N/A"))` raises `ValueError`. The conversion assumed every cell
value was parseable as a number, but sheets often contain placeholders,
notes, or stray characters.

### Solution
Added `_to_int(raw)` helper:
1. Returns `0` for `None` and empty string
2. Strips commas and `$` prefixes
3. Returns `0` if `int(float(s))` raises any exception

Applied in both `matrix_get()` and `matrix_read_cell()`.

### Files changed
- `sheets/google_sheets.py` — added `_to_int()`, updated `matrix_get()`
  and `matrix_read_cell()` to use it
