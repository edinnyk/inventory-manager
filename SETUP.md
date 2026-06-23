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
4. Scroll down to **Privileged Gateway Intents** and enable:
   - **Message Content Intent** → ON
5. Go to the **Installation** tab (left sidebar)
6. Under **Install Link**, select **Discord Provided Link** from the dropdown
7. Under **Default Install Settings**, add these scopes:
   - **Guild Install**: check `bot` and `applications.commands`
   - When you check `bot`, permissions appear — select **Send Messages**
8. Copy the install link from the **Install Link** section at the top
9. Open that URL in your browser → select your server → **Authorize**

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
3. Click **Share** → add the service account email (it looks like `inventory-bot@your-project.iam.gserviceaccount.com` — find it at the top of the JSON file) → set **Editor** permissions → Send
4. Copy the **Sheet ID** from the URL:
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

Create a repository on GitHub first (free, public or private) — don't add a README or .gitignore when creating it.

---

## Step 6 — Deploy on Railway

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `inventory-manager` repository
5. Railway detects `requirements.txt` and installs dependencies automatically
6. Go to the **Variables** tab and add:
   - `DISCORD_TOKEN` → paste your bot token
   - `GOOGLE_SERVICE_ACCOUNT_JSON` → paste the **entire JSON contents** from `credentials.json` (not the filename!)
   - `SHEET_ID` → paste your sheet ID
7. Railway will restart the bot automatically

---

## Step 7 — Test It

In your Discord server, type:

```
/inv 5 laptops, 10 mice, and 3 monitors
```

The bot should reply with a summary. Check your Google Sheet — the rows should appear.

---

## Troubleshooting

| Problem | Likely Fix |
|---------|------------|
| Bot doesn't respond | Check `DISCORD_TOKEN` is correct in Railway variables |
| Sheet not writing | Make sure the service account email has **Editor** access on the sheet |
| Railway deploy fails | Check the **Deploy Logs** tab for errors |
| `/inv` says "not found" | Slash commands can take a few minutes to sync. Wait 2-3 minutes |

---

## Optional: Enable AI Categorization

Get an API key from an OpenAI-compatible provider and add it to Railway variables:

| Provider | Base URL | Model | Free Tier |
|----------|----------|-------|-----------|
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini` | No |
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-chat` | No, but cheap |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `deepseek-chat` (or many others) | Some free models |

In Railway variables, set:
- `OPENAI_API_KEY` = your key
- `AI_BASE_URL` = the provider's base URL
- `AI_MODEL` = the model name you want

Then in Discord, type `/toggle-ai` to enable it.

---

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/inv` | Add items to inventory | `/inv 5 laptops and 3 chairs` |
| `/categories` | List all categories and subcategories | `/categories` |
| `/add-cat` | Add a custom category | `/add-cat Beverages soda, juice, water` |
| `/add-subcat` | Add a subcategory to an existing category | `/add-subcat Electronics Peripherals mouse, keyboard` |
| `/remove-cat` | Remove a custom category | `/remove-cat Beverages` |
| `/remove-subcat` | Remove a subcategory | `/remove-subcat Electronics Peripherals` |
| `/sync-categories` | Write all categories to the "Categories" sheet tab | `/sync-categories` |
| `/recent` | Show recent entries (add a number for more) | `/recent 10` |
| `/sheet` | Get the Google Sheet link | `/sheet` |
| `/toggle-ai` | Enable/disable AI categorization | `/toggle-ai` |
| `/diag` | Test connection to Google Sheets | `/diag` |

---

## Replication Guide

Use this section to duplicate the bot for another business.

### What to change per business

1. **Fork the repo** on GitHub (or copy the folder)
2. **Create a new Google Sheet** and get its `SHEET_ID`
3. **Create a new Discord bot** at https://discord.com/developers/applications and get its `DISCORD_TOKEN`
4. **Create a new Google Cloud service account** (or reuse the same one and share the new sheet with it)
5. **Deploy on Railway** — create a new project and add the three variables:
   - `DISCORD_TOKEN`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `SHEET_ID`

### What stays the same

- The code itself (no changes needed unless you want custom categories)
- The `DISCORD_TOKEN`, `SHEET_ID`, and `GOOGLE_SERVICE_ACCOUNT_JSON` are all per-deployment, stored in Railway variables

### Customizing per business

Edit these files if you need different defaults:

| File | What to change |
|------|---------------|
| `parser/categories.py` | `DEFAULT_CATEGORIES` — top-level categories and `SUBCATEGORIES` — subcategories |
| `sheets/schema.py` | `HEADERS` — column layout of the inventory sheet |

### Business-specific inventory framework

Each business can define its own category/subcategory structure:

```python
DEFAULT_CATEGORIES = {
    "Restaurant": ["ingredient", "produce", "meat", "dairy"],
    "Bar": ["spirit", "liquor", "beer", "wine", "mixer"],
}
SUBCATEGORIES = {
    "Restaurant": {
        "Produce": ["lettuce", "tomato", "onion"],
        "Meat": ["chicken", "beef", "pork"],
    },
    "Bar": {
        "Spirits": ["vodka", "whiskey", "gin"],
        "Beer": ["lager", "ipa", "stout"],
    },
}
```

### Quick duplicate checklist

```
☐ Fork repo / copy code
☐ Create new Google Sheet → share with service account
☐ Create new Discord app → copy token
☐ (Optional) Create new Google Cloud service account
☐ Deploy on Railway with 3 variables
☐ Test with `/diag` and `/inv 5 test chairs`
```
