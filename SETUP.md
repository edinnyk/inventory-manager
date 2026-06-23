# Inventory Manager — Setup Guide

## Prerequisites

- A Discord account + a server where you can test the bot
- A Google account (Gmail/Workspace)
- A GitHub account (free)

---

## Step 1 — Create a Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it "Inventory Manager" → Create
3. Go to the **Bot** tab (left sidebar) — the bot user is created automatically.
   Under the **Token** section, click **Reset Token** then **Copy**
   - Save this token — you'll need it later as `DISCORD_TOKEN`
4. Go to the **Installation** tab (left sidebar)
5. Under **Install Link**, select **Discord Provided Link** from the dropdown
6. Under **Default Install Settings**, add these scopes:
   - **Guild Install**: check `bot` and `applications.commands`
7. Copy the install link from the **Install Link** section at the top
8. Open that URL in your browser → select your server → **Authorize**

---

## Step 2 — Get Google Sheets API Credentials

1. Go to https://console.cloud.google.com
2. Create a new project (or select existing)
3. Go to **APIs & Services → Library**
4. Search for "Google Sheets API" → Enable it
5. Go to **Credentials** → **Create Credentials** → **Service Account**
6. Name it "inventory-bot" → Create → Done
7. Click on the service account you just created
8. Go to the **Keys** tab → **Add Key** → **Create New Key**
9. Choose **JSON** → Download the file
   - Save this as `credentials.json` in the project folder
10. Open the file in a text editor and copy the **full contents** (you'll also need to paste it into Railway later)

---

## Step 3 — Create the Google Sheet

1. Go to https://sheets.new
2. Name it "Inventory Manager"
3. Rename the first tab to **"Inventory"**
4. Add your variant headers in row 1 starting at column E (e.g. MAPLE, CHERRY, ESPRESSO, WHITE, GRAY)
5. Add a **second tab** named **"Audit Log"** (the bot creates this automatically, but you can create it now)
6. Click **Share** → add the service account email (looks like `inventory-bot@your-project.iam.gserviceaccount.com`) → set **Editor** permissions → Send
7. Copy the **Sheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit`
   - Save this as `SHEET_ID`

---

## Step 4 — Create the .env File

In the `InventoryManager` folder, create a file called `.env`:

```
DISCORD_TOKEN=your_discord_bot_token_here
GOOGLE_SERVICE_ACCOUNT_JSON=credentials.json
SHEET_ID=your_google_sheet_id_here
```

Replace the values with what you saved in Steps 1-3.

---

## Step 5 — Push to GitHub

```cmd
cd "C:\Users\edinn\InventoryManager"
git remote add origin https://github.com/YOUR_USERNAME/inventory-manager.git
git branch -M main
git push -u origin main
```

Create a repository on GitHub first (free, public or private).

---

## Step 6 — Deploy on Railway

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `inventory-manager` repository
5. Go to the **Variables** tab and add:
   - `DISCORD_TOKEN` → paste your bot token
   - `GOOGLE_SERVICE_ACCOUNT_JSON` → paste the **entire JSON contents** from `credentials.json`
   - `SHEET_ID` → paste your sheet ID
6. Railway will restart the bot automatically

---

## Step 7 — Test It

```
/add BPP09 3 maple 5 cherry
```

The bot should reply with before/after values. Check the Inventory tab to see the cells updated,
and the Audit Log tab to see the timestamped entry.

---

## Troubleshooting

| Problem | Likely Fix |
|---------|------------|
| Bot doesn't respond | Check `DISCORD_TOKEN` is correct in Railway variables |
| Sheet not writing | Make sure the service account email has **Editor** access on the sheet |
| "Product not found" | Use `/add-product BPP09` to create it first, or check column B for typos |
| "Variant not found" | Use `/add-variant MAPLE` to create it, or check the spelling |
| Railway deploy fails | Check the **Deploy Logs** tab for errors |

---

## Command Reference

| Command | Example | What it does |
|---------|---------|--------------|
| `/add` | `/add BPP09 3 maple 5 cherry` | Adds to variant quantities |
| `/sub` | `/sub BPP09 2 maple` | Subtracts from variant (won't go below 0) |
| `/set` | `/set BPP09 10 maple` | Sets exact quantity |
| `/stock` | `/stock BPP09` | Shows all variant totals |
| `/log` | `/log BPP09 10` | Shows last 10 audit entries |
| `/add-product` | `/add-product NEWPROD 24` | Adds a new product row |
| `/add-variant` | `/add-variant OAK` | Adds a new variant column |
| `/rename-variant` | `/rename-variant GRAY GREY` | Renames a variant column header |
| `/sheet` | `/sheet` | Sends the sheet link |

### Input formats accepted by `/add`, `/sub`, `/set`

All of these work:

```
/add BPP09 3 maple 5 cherry
/add BPP09 maple 3 cherry 5
/add BPP09 maple:3 cherry:5
/add BPP09 3x maple 5x cherry
/add BPP09 3 maple, 5 cherry
/add BPP09 maple:3, 5 cherry and 2x OAK
```

First token is always the product name. After that, any mix of `qty variant`, `variant qty`,
`variant:qty`, `qtyx variant`, separated by spaces, commas, `and`, or `&`.

---

## Replication Guide

Use this to duplicate the bot for a new business.

### What you need per deployment

| Asset | How to create it | Owned by |
|-------|-----------------|----------|
| Discord bot | Discord Developer Portal → New Application | You (or client) |
| Google Sheet | sheets.new → Share with your service account | Client (you control access) |
| Railway project | Railway → New Project → Deploy from GitHub repo | You |

### Step-by-step

1. **Create Discord bot**: Developer Portal → New App → Bot tab → Reset Token → copy
2. **Create Google Sheet**: sheets.new → name it → rename first tab to "Inventory" → add variant headers in row 1 starting at column E → add second tab "Audit Log" → Share with your service account email as Editor
3. **Deploy on Railway**: New Project → Deploy from GitHub repo → set 3 variables:
   - `DISCORD_TOKEN` = token from step 1
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = your full service account JSON
   - `SHEET_ID` = ID from the sheet URL
4. **Test**: `/add-product SAMPLE` then `/add SAMPLE 3 maple`

### One codebase, many deployments

Same GitHub repo works for every client. Only the 3 Railway variables change:

```
Project: ClientA-inventory       Project: ClientB-inventory
  DISCORD_TOKEN=xxx                DISCORD_TOKEN=yyy
  SHEET_ID=aaa                     SHEET_ID=bbb
  GOOGLE_SERVICE_ACCOUNT_JSON=...  GOOGLE_SERVICE_ACCOUNT_JSON=...
```

### To remove a client's access

1. Railway → delete their project (kills the bot)
2. Google Sheet → unshare with your service account (kills sheet access)
3. Discord → kick the bot from the server (optional)
