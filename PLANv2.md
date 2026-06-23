# Inventory Manager v2 — Plan & Replication Guide

## Overview

Rewrite from a flat audit-log + category-based system to a **matrix inventory system**.
Two tabs in the same Google Sheet:

| Tab | Purpose |
|-----|---------|
| **Inventory** | Matrix — products on rows, variants on columns, quantities in cells |
| **Audit Log** | Flat history — every add/sub/set logged with timestamp |

No more categories, AI, or natural language parsing. The bot reads the sheet structure
dynamically (discovers product IDs and variant columns at runtime).

---

## Architecture

```
User: "/add BPP09 3 maple 5 cherry"
        ↓
bot/handlers.py — parses command, extracts product + pairs
        ↓
sheets/google_sheets.py:
  1. find_product_row("BPP09") → row number in "Inventory" tab
  2. find_variant_col("maple") → column letter in "Inventory" tab
  3. matrix_read_cell(row, col) → current value (or 0)
  4. matrix_write_cell(row, col, new_val)
  5. log_entry("BPP09", "+3", "MAPLE +5 CHERRY") → append to "Audit Log"
```

---

## Implementation Steps

### Step 1 — Remove unused files (`opencode` does this)

- Delete `parser/` folder (4 files: extractor, categories, categorizer, ai_categorizer)
- Update `main.py` to remove parser imports
- Update `requirements.txt` to remove `openai`

### Step 2 — Update schema (`opencode` does this)

- `sheets/schema.py`: update `HEADERS` for audit log, add column-letter helper

### Step 3 — Build matrix + audit log engine (`opencode` does this)

- `sheets/google_sheets.py`:
  - `_ensure_headers()` → now targets "Audit Log" tab
  - `log_entry(item, delta, notes)` → appends timestamped row
  - `find_product_row(product)` → scans column B in "Inventory" tab
  - `find_variant_col(variant)` → scans row 1 columns E+ in "Inventory" tab
  - `matrix_read_cell(row, col)` → returns integer (0 if empty)
  - `matrix_write_cell(row, col, val)` → updates a single cell
  - `matrix_get(product)` → returns dict of all variants for that product
  - `add_product_row(product, size)` → appends new row to matrix
  - `add_variant_column(name)` → appends new column after last variant
  - `rename_variant_column(old, new)` → updates header cell

### Step 4 — Build flexible parser (`opencode` does this)

- New `parser/pairs.py` — single function that accepts all formats:
  - `3 maple 5 cherry`
  - `maple 3 cherry 5`
  - `maple:3 cherry:5`
  - `3x maple 5x cherry`
  - `3 maple, 5 cherry`
  - Mixed: `maple:3, 5 cherry and 2x OAK`

### Step 5 — Build commands (`opencode` does this)

- `bot/handlers.py`: full rewrite with 10 commands

### Step 6 — Update setup docs (`opencode` does this)

- `SETUP.md`: update command reference

### Step 7 — Commit and push (`YOU` do this)

- `git push` from Windows terminal

### Step 8 — Redeploy (`YOU` do this)

- Trigger **Redeploy** on Railway dashboard

---

## Command Reference (v2)

| Command | Example | What it does |
|---------|---------|--------------|
| `/add` | `/add BPP09 3 maple 5 cherry` | Adds 3 to MAPLE, 5 to CHERRY for product BPP09 |
| `/sub` | `/sub BPP09 2 maple` | Subtracts 2 from MAPLE (won't go below 0) |
| `/set` | `/set BPP09 10 maple` | Sets MAPLE to exactly 10 |
| `/stock` | `/stock BPP09` | Shows current totals for all variants of BPP09 |
| `/log` | `/log BPP09 10` | Shows last 10 audit entries for BPP09 |
| `/add-product` | `/add-product NEWPROD 24` | Adds new product with size 24 |
| `/add-variant` | `/add-variant OAK` | Appends a new variant column |
| `/rename-variant` | `/rename-variant GRAY GREY` | Renames variant header |
| `/sheet` | `/sheet` | Sends the sheet link |

---

## Spreadsheet Layout

### Tab: "Inventory" (first tab)

| B | C | D | E | F | G |
|---|---|---|---|---|---|
| **SIZE** | | | **MAPLE** | **CHERRY** | **ESPRESSO** |
| BPP09 | 16 | | 13 | 3 | 5 |
| B09 | 0 | | 11 | 16 | 3 |

- **Row 1**: variant headers (columns E+)
- **Column B**: product IDs
- **Column C**: size (optional, user-managed)
- **Cells E2+**: quantities (bot reads/writes here)

### Tab: "Audit Log" (second tab)

| Item | Quantity | Date | Notes |
|------|----------|------|-------|
| BPP09 | +3 | 2026-06-22 14:30 | Added 3 MAPLE, 5 CHERRY |
| BPP09 | -2 | 2026-06-22 15:10 | Subtracted 2 MAPLE |

---

## How to Duplicate for a New Business

### What you need per deployment

| Asset | How to create it | Owned by |
|-------|-----------------|----------|
| Discord bot | https://discord.com/developers/applications → New Application | You (or client's Discord account) |
| Google Sheet | https://sheets.new → Share with your service account email | Client (you control access via your service account) |
| Railway project | Railway dashboard → New Project → Deploy from GitHub repo | You |

### Step-by-step

1. **Fork or branch** the repo (optional — only if you need different defaults)
2. **Create Discord bot**:
   - Go to Discord Developer Portal → New Application → name it
   - Bot tab → Reset Token → copy token
   - Installation tab → generate invite link with `bot` + `applications.commands` scopes
   - Open invite link → add to the client's server
3. **Create Google Sheet**:
   - Go to https://sheets.new → name it
   - Share → add your service account email (e.g. `inventory-bot@your-project.iam.gserviceaccount.com`) as **Editor**
   - Name the first tab "Inventory"
   - Add your variant headers in row 1 (starting at column E)
4. **Deploy on Railway**:
   - Railway dashboard → New Project → Deploy from GitHub repo
   - Select your repo (or fork)
   - Add 3 variables:
     - `DISCORD_TOKEN` = token from step 2
     - `GOOGLE_SERVICE_ACCOUNT_JSON` = your full service account JSON
     - `SHEET_ID` = the ID from the sheet URL
   - Railway auto-deploys

### To remove a client's access

1. Railway → delete their project (kills the bot)
2. Google Sheet → unshare with your service account (kills sheet access)
3. Discord → kick the bot from the server (optional — it's dead without Railway)

### One codebase, many deployments

The same GitHub repo works for every client. Only the 3 Railway variables change:

```
Project: ClientA-inventory
  DISCORD_TOKEN=xxx
  SHEET_ID=aaa
  GOOGLE_SERVICE_ACCOUNT_JSON=... (same JSON for all)

Project: ClientB-inventory
  DISCORD_TOKEN=yyy
  SHEET_ID=bbb
  GOOGLE_SERVICE_ACCOUNT_JSON=... (same JSON for all)
```

If a client needs fundamentally different logic (e.g. different variant matching rules),
create a branch per client and deploy from that branch.

---

## What I (opencode) will do

- Write all code changes
- Create the plan document
- Verify files are consistent

## What YOU will do

- Commit: `git push` from Windows terminal
- Trigger **Redeploy** on Railway dashboard
- Test: `/add BPP09 3 maple 5 cherry`
- Set up new clients following the duplication guide above
