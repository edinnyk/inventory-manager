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

```bash
cd "C:\Users\edinn\OneDrive\Desktop\InventoryManager"
git init
git add .
git commit -m "Initial commit"
```

Then create a repository on GitHub (free, public or private) and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/inventory-manager.git
git branch -M main
git push -u origin main
```

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

1. Get an OpenAI API key from https://platform.openai.com/api-keys (costs ~$0.01 per 100 items)
2. Add it to Railway variables: `OPENAI_API_KEY=sk-your-key-here`
3. In Discord, type `/toggle-ai` to enable it
