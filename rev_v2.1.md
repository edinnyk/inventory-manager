# Inventory Manager — rev v2.1

## Complete Function Reference

---

### `config.py` — Environment variables & credentials

| Variable / Function | What it does |
|---------------------|--------------|
| `DISCORD_TOKEN` | Discord bot token loaded from env. Bot fails to start if missing. |
| `SHEET_ID` | Google Sheet ID loaded from env. Auto-extracts ID from full URL if a URL is pasted instead. Fails if missing. |
| `get_google_credentials()` | Lazy-loads the Google service account JSON (cached after first call). Accepts raw JSON string or a file path from `GOOGLE_SERVICE_ACCOUNT_JSON` env var. Strips surrounding quotes. Returns a dict. |
| `OPENAI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` | Legacy — still read from env but unused in v2. Safe to leave in Railway variables or delete them. |

**Potential issues:** If `GOOGLE_SERVICE_ACCOUNT_JSON` is neither valid JSON nor a file path, `get_google_credentials()` raises an error. The bot can still start (the error is caught in `main.py`), but any command that reads/writes the sheet will fail.

---

### `main.py` — Entry point

| Step | What it does |
|------|--------------|
| Lines 1-8 | Sets up Python logging (timestamp, level, module name) |
| Lines 10-55 | **Startup diagnostics** — logs Python version, Discord token length, Sheet ID, attempts to load Google credentials and test the Sheets API. All errors are caught and logged — the bot starts regardless. |
| Lines 57-63 | Imports `bot.discord_bot` (creates the Discord client + command tree), imports `bot.handlers` (registers all slash commands), then calls `bot.run()` |

**Potential issues:** If `import bot.handlers` fails (e.g., missing dependency or syntax error), the bot crashes at line 58 before reaching `bot.run()`. This would show up in Railway deploy logs as a traceback.

---

### `bot/discord_bot.py` — Discord client & command tree

| Object / Function | What it does |
|-------------------|--------------|
| `intents` | Discord gateway intents — enables `message_content` intent (required for reading message content) |
| `bot` | `discord.Client` instance — the main connection to Discord |
| `tree` | `app_commands.CommandTree` — registry for all slash commands |
| `on_ready()` | Called when bot connects to Discord. **Syncs all slash commands to each guild the bot is in.** Guild sync = commands appear instantly (vs. global sync which takes hours). |

**Potential issues:** If `on_ready` crashes (line 19 try/except catches it), commands won't be synced and won't show up in Discord. The bot would appear "online" but have zero commands.

---

### `bot/handlers.py` — All slash command implementations

#### `_val(v: int) -> str`
Formats an integer as a signed string: `+3` or `-2`. Used in audit log entries.

#### `_process_pairs(interaction, product, pairs_text, operation)`
Core logic shared by `/add`, `/sub`, `/set`. Steps:
1. Defers the Discord response (gives us 15 min to process)
2. Calls `parse_pairs()` on the text to extract variant/quantity pairs
3. Looks up the product row in the Inventory tab via `find_product_row()`
4. Builds a lookup dict of all variant names for case-insensitive matching
5. For each variant/qty pair:
   - Finds the variant column via `var_lookup`
   - Reads current cell value via `matrix_read_cell()`
   - Computes new value based on operation (add, sub, set)
   - Writes new value via `matrix_write_cell()`
6. Logs the changes to the Audit Log tab via `log_entry()`
7. Sends a Discord embed with before/after values and any errors

**Potential issues:**
- If "Inventory" tab doesn't exist, `find_product_row()` calls `_tab_info()` which raises `RuntimeError("Tab 'Inventory' not found")` — user sees error
- If product doesn't exist in column B, user gets a suggestion to use `/add-product`

#### `add(interaction, product, pairs)` — `/add`
Calls `_process_pairs()` with operation="add". Adds quantities to existing cell values.

#### `sub(interaction, product, pairs)` — `/sub`
Calls `_process_pairs()` with operation="sub". Subtracts quantities, capped at 0.

#### `set_(interaction, product, pairs)` — `/set`
Calls `_process_pairs()` with operation="set". Sets absolute values, computes the delta for the audit log.

#### `stock(interaction, product)` — `/stock`
Calls `matrix_get()` to read all variant values for the product, returns an embed with the data.

#### `log(interaction, product, n)` — `/log`
Calls `get_log()` to read the Audit Log tab, filters by product name, returns last N entries (default 5).

#### `add_product(interaction, product, size)` — `/add-product`
Checks if product already exists (prevents duplicates), calls `add_product_row()` to append a new row to the Inventory tab, logs "Product added" to the audit.

#### `add_variant(interaction, name)` — `/add-variant`
Calls `add_variant_column()` to append a new column to the right of all existing variant columns. Writes the name in row 1.

#### `rename_variant(interaction, old, new)` — `/rename-variant`
Calls `rename_variant_column()` which finds the column by old name and updates the header cell.

**Potential issues:**
- Function name `set_` has trailing underscore because `set` is a Python reserved keyword. The Discord command name is still `set`.

---

### `sheets/schema.py` — Column definitions

| Constant | Value | Purpose |
|----------|-------|---------|
| `HEADERS` | `["Item", "Quantity", "Date", "Notes"]` | Column headers for the Audit Log tab |

---

### `sheets/google_sheets.py` — All Google Sheets API calls

#### Internal helpers

| Function | What it does |
|----------|--------------|
| `_get_authorized_session()` | Loads Google credentials, refreshes the access token, creates a `requests.Session` with the `Authorization: Bearer` header. Called at the start of every API interaction. |
| `_range(sheet_name, cols)` | Formats an A1 range string. Wraps sheet name in single quotes if it contains special characters (e.g., `'Audit Log'!A:D`). |
| `_col_letter(n)` | Converts a 1-based column number to a letter (1=A, 2=B, ..., 27=AA, etc.). Used when dynamically mapping variant columns. |
| `_tab_info(tab_name, auto_create=False)` | Fetches spreadsheet metadata from the Sheets API, searches for a tab by name. Returns `(session, sheet_title, sheet_id)`. If `auto_create=True` and the tab doesn't exist, creates it via `batchUpdate`. |
| `_ensure_audit_headers(session, sheet_name, sheet_id)` | Checks if the Audit Log tab already has the correct header row. If not, writes headers using `batchUpdate` with the specific `sheetId` (avoids writing to wrong tab). |
| `_last_data_row(session, sheet_name, column)` | Scans a column from bottom to top, returns the next empty row number after the last non-empty cell. Used to find where to append new products. |

**Potential issues with `_tab_info`:**
- Makes a full metadata API call every time (not cached). For a Discord bot this is fine — ~100ms overhead.
- If the sheet doesn't exist or the service account doesn't have access, raises `RuntimeError`.

**Potential issues with `_ensure_audit_headers`:**
- The correct `sheetId` must be passed — earlier bug was hardcoded to `0` which corrupted the first tab.

#### Audit Log functions

| Function | What it does |
|----------|--------------|
| `log_entry(item, delta, notes)` | Auto-creates "Audit Log" tab if missing, ensures headers, appends a row with `[item, delta, timestamp, notes]` using the `:append` API endpoint. |
| `get_log(product, n)` | Reads all rows from Audit Log, filters by product name (case-insensitive), returns last N as dicts with keys `item`, `delta`, `date`, `notes`. |

**Potential issues:**
- `log_entry` is called from `_process_pairs` — if it fails, the matrix write already happened but logging fails. The user still sees the embed (matrix write succeeded) but audit trail is missing.

#### Matrix (Inventory tab) functions

| Function | What it does |
|----------|--------------|
| `find_product_row(product)` | Reads column B of Inventory tab, scans for exact case-insensitive match. Returns 1-based row number or `None`. |
| `find_variant_col(variant)` | Reads row 1 of Inventory tab starting at column E, scans for exact case-insensitive match. Returns column letter (e.g., "F") or `None`. |
| `list_variants()` | Returns all non-empty values from row 1 columns E+ as a list of strings. |
| `matrix_read_cell(product, variant)` | Finds product row + variant column, reads the value. Handles empty cells (returns 0). Strips commas and dollar signs before converting to int. |
| `matrix_write_cell(product, variant, value)` | Finds product row + variant column, overwrites the cell with a string number. |
| `matrix_get(product)` | Reads all values from the product's row across all variant columns, returns a dict `{variant_name: quantity}`. |
| `add_product_row(product, size)` | Appends a new row at the bottom of the Inventory tab. Writes product to column B and optional size to column C. |
| `add_variant_column(name)` | Finds the next empty column after the last variant, writes the name to row 1. Reports error if variant already exists. |
| `rename_variant_column(old, new)` | Finds the column by old name, overwrites row 1 with new name. |

**Potential issues:**
- `find_product_row` and `find_variant_col` each call `_tab_info` independently, making 2 API calls per lookup. `matrix_read_cell` and `matrix_write_cell` each call them separately too — a single `/add BPP09 3 maple` makes ~5 API calls. This is acceptable for a Discord bot but won't scale to hundreds of concurrent users.
- `add_product_row` uses `_last_data_row` which reads the entire column B. On a sheet with thousands of rows, this is slow but still within Discord's 15-second timeout.
- `matrix_read_cell` uses `int(float(...))` which handles decimals but truncates them (e.g., `3.7` becomes `3`). Pure integers are unaffected.

---

### `parser/pairs.py` — Flexible input parser

| Component | What it does |
|-----------|--------------|
| `PAIR_RE` | Regex with 3 alternatives: `qty variant`, `variant:qty`, `variant qty`. Named groups prevent overlap. |
| `SEPARATORS` | Splits on `,`, `and`, `&` with optional surrounding whitespace. |
| `parse_pairs(text)` | Splits text by separators → runs regex on each segment → extracts `(variant, qty)` pairs → deduplicates by variant name (case-insensitive, first occurrence wins). |

**Supported input formats:**
```
/add BPP09 3 maple 5 cherry        → [("maple", 3), ("cherry", 5)]
/add BPP09 maple 3 cherry 5        → [("maple", 3), ("cherry", 5)]
/add BPP09 maple:3 cherry:5        → [("maple", 3), ("cherry", 5)]
/add BPP09 3x maple 5x cherry      → [("maple", 3), ("cherry", 5)]
/add BPP09 3 maple, 5 cherry       → [("maple", 3), ("cherry", 5)]
/add BPP09 3 maple and 5 cherry    → [("maple", 3), ("cherry", 5)]
/add BPP09 hard maple:3 cherry:5   → [("hard maple", 3), ("cherry", 5)]
```

**Potential issues:**
- Variant names cannot contain digits (e.g., `3m cable` won't parse correctly — `3` is consumed as quantity). The regex stops `[a-zA-Z/&-]` before digits.
- Deduplication uses lowercase variant name, so `Maple` and `maple` produce one entry (first occurrence wins).
- Maximum-pair-per-command is limited by Discord's 4000-character input limit and the 15-minute defer timeout.

---

## What Changed from v1 to v2

| Topic | v1 (old) | v2 (current) |
|-------|----------|--------------|
| **Data model** | Flat log — each entry appends a row | Matrix — products × variants, cells are totals |
| **Sheet tabs** | One tab (data) + Category reference tab | Two tabs: "Inventory" (matrix) + "Audit Log" (history) |
| **Commands** | `/inv`, `/categories`, `/add-cat`, `/add-subcat`, `/remove-cat`, `/remove-subcat`, `/sync-categories`, `/recent`, `/toggle-ai`, `/diag` | `/add`, `/sub`, `/set`, `/stock`, `/log`, `/add-product`, `/add-variant`, `/rename-variant`, `/sheet` |
| **AI** | Optional OpenAI/DeepSeek categorization | Removed entirely |
| **Categories** | Keyword-based category matching | No categories — variants are user-defined columns |
| **Input parser** | Natural language ("5 laptops") | Structured pairs ("3 maple 5 cherry") |
| **Dependencies** | `gspread`, `openai`, `discord.py`, `google-auth`, `python-dotenv` | `discord.py`, `google-auth`, `requests`, `python-dotenv` |
| **Files removed** | (none) | `parser/extractor.py`, `parser/categories.py`, `parser/categorizer.py`, `parser/ai_categorizer.py`, `PLAN.txt` |
| **Files added** | (none) | `parser/pairs.py`, `PLANv2.md` |

---

## Deployment Troubleshooting

### Symptoms of stale deployment

Bot connects to Discord, shows as online, but:
- Old commands still work (e.g., `/diag`, `/inv`)
- New commands don't appear (`/add`, `/stock`, etc.)
- Railway deploy logs show the old commit hash

### Root cause

Railway's **Redeploy** button often reuses the previous build artifact instead of fetching fresh code from GitHub. The code on GitHub is correct, but Railway is running a cached build.

### Verified fixes (in order)

1. **Push an empty commit** — forces Railway's GitHub webhook to fire:
   ```cmd
   git commit --allow-empty -m "force rebuild"
   git push
   ```

2. **Disconnect and reconnect the repo** in Railway Settings

3. **Delete Railway environment and create a new one** — this is the nuclear option but always works:
   - Railway dashboard → project → **Settings** → scroll to **Danger Zone**
   - Delete the environment
   - **Generate New Environment**
   - Set the 3 env vars again
   - Railway builds fresh from latest GitHub commit

### Verifying the correct code is deployed

Check Railway **Deploy Logs** for:
- The commit hash at the top of the build log should be `504ea6c` or later
- The `on_ready` message should log: `synced commands to guild...`
- Type `/stock` in Discord — if v2 is running, it should appear in the command list

---

## Quick Reference: Data Flow

```
User types "/add BPP09 3 maple 5 cherry"
        ↓
Discord API receives interaction
        ↓
Discord.py routes to `handlers.add()`
        ↓
`_process_pairs()` is called
    ├── `parse_pairs("3 maple 5 cherry")` → [("maple", 3), ("cherry", 5)]
    ├── `find_product_row("BPP09")` → row 2 (scans column B)
    ├── `list_variants()` → ["MAPLE", "CHERRY", "ESPRESSO", ...] (reads row 1)
    │
    ├── For "maple", 3:
    │   ├── `find_variant_col("maple")` → "E" (scans row 1)
    │   ├── `matrix_read_cell("BPP09", "maple")` → 13 (reads cell E2)
    │   └── `matrix_write_cell("BPP09", "maple", 16)` → writes to cell E2
    │
    ├── For "cherry", 5:
    │   ├── `find_variant_col("cherry")` → "F"
    │   ├── `matrix_read_cell("BPP09", "cherry")` → 3 (reads cell F2)
    │   └── `matrix_write_cell("BPP09", "cherry", 8)` → writes to cell F2
    │
    └── `log_entry("BPP09", "+8", "MAPLE: 13 → 16 (+3); CHERRY: 3 → 8 (+5)")`
        └── Appends row to "Audit Log" tab
```
