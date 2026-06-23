from datetime import datetime

import discord

from bot.discord_bot import tree
from config import SHEET_ID
from parser.categorizer import categorize_items
from parser.categories import DEFAULT_CATEGORIES, SUBCATEGORIES, all_keywords, all_subcategories
from parser.extractor import extract_items
from sheets.google_sheets import append_entry, get_recent, sync_categories_tab

custom_categories: dict[str, list[str]] = {}
custom_subcategories: dict[str, dict[str, list[str]]] = {}
ai_enabled = False

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"


@tree.command(name="inv", description="Add items to inventory")
async def inv(interaction: discord.Interaction, items: str):
    await interaction.response.defer()

    try:
        parsed = extract_items(items)
        if not parsed:
            await interaction.followup.send("Couldn't parse any items. Try: `/inv 5 laptops and 3 chairs`")
            return

        categorized = categorize_items(parsed, use_ai=ai_enabled, custom_categories=custom_categories, custom_subcategories=custom_subcategories)

        lines = []
        for item_name, category, subcategory, quantity in categorized:
            append_entry(item_name, category, quantity, subcategory=subcategory)
            cat_str = f"{category} > {subcategory}" if subcategory else category
            lines.append(f"**{item_name}** — {quantity} ({cat_str})")

        embed = discord.Embed(
            title="Inventory Added",
            description="\n".join(lines),
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"View sheet: {SHEET_URL}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        msg = str(e)[:500]
        await interaction.followup.send(f"Error: {msg}")


@tree.command(name="categories", description="List all categories and subcategories")
async def categories(interaction: discord.Interaction):
    all_cats = all_keywords(custom_categories)
    all_subs = all_subcategories(custom_subcategories)
    lines = []
    for cat in sorted(all_cats):
        subs = all_subs.get(cat, {})
        if subs:
            top_row = f"**{cat}**"
            for subcat in sorted(subs):
                kw = ", ".join(sorted(set(subs[subcat])))
                top_row += f"\n  └ {subcat}: {kw}"
            lines.append(top_row)
            used_kw = set()
            for lst in subs.values():
                for k in lst:
                    used_kw.add(k)
            remaining = [k for k in all_cats[cat] if k not in used_kw]
            if remaining:
                lines[-1] += f"\n  ─ (general): {', '.join(sorted(set(remaining)))}"
        else:
            kw = ", ".join(sorted(set(all_cats[cat])))
            lines.append(f"**{cat}**: {kw}")

    embed = discord.Embed(
        title="Inventory Categories",
        description="\n".join(lines),
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="add-cat", description="Add a custom category with keywords")
async def add_category(interaction: discord.Interaction, name: str, keywords: str):
    custom_categories[name] = [kw.strip().lower() for kw in keywords.split(",")]
    await interaction.response.send_message(
        f"Category **{name}** added with keywords: {keywords}",
        ephemeral=True,
    )


@tree.command(name="add-subcat", description="Add a subcategory to an existing category")
async def add_subcategory(interaction: discord.Interaction, category: str, name: str, keywords: str):
    if category not in custom_subcategories:
        custom_subcategories[category] = {}
    custom_subcategories[category][name] = [kw.strip().lower() for kw in keywords.split(",")]
    await interaction.response.send_message(
        f"Subcategory **{name}** added to **{category}** with keywords: {keywords}",
        ephemeral=True,
    )


@tree.command(name="remove-cat", description="Remove a custom category")
async def remove_category(interaction: discord.Interaction, name: str):
    if name in custom_categories:
        del custom_categories[name]
        custom_subcategories.pop(name, None)
        await interaction.response.send_message(f"Category **{name}** removed.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Category **{name}** not found.", ephemeral=True)


@tree.command(name="remove-subcat", description="Remove a subcategory")
async def remove_subcategory(interaction: discord.Interaction, category: str, name: str):
    subs = custom_subcategories.get(category)
    if subs and name in subs:
        del subs[name]
        if not subs:
            del custom_subcategories[category]
        await interaction.response.send_message(f"Subcategory **{name}** removed from **{category}**.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Subcategory **{name}** not found under **{category}**.", ephemeral=True)


@tree.command(name="sync-categories", description="Write all categories to the Categories sheet tab")
async def sync_categories(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        sync_categories_tab(all_keywords(custom_categories), all_subcategories(custom_subcategories))
        await interaction.followup.send("Categories synced to the **Categories** sheet tab.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Sync failed: {e}", ephemeral=True)


@tree.command(name="sheet", description="Get the Google Sheet link")
async def sheet(interaction: discord.Interaction):
    await interaction.response.send_message(SHEET_URL)


@tree.command(name="recent", description="Show recent inventory entries")
async def recent(interaction: discord.Interaction, n: int = 5):
    try:
        rows = get_recent(n)
        if not rows:
            await interaction.response.send_message("No entries yet.")
            return

        lines = []
        for row in reversed(rows):
            padded = row + [""] * (7 - len(row))
            item, cat, subcat, qty, date_ = padded[0], padded[1], padded[2], padded[3], padded[4]
            cat_str = f"{cat} > {subcat}" if subcat else cat
            lines.append(f"**{item}** | {qty}x {cat_str} — {date_}")

        embed = discord.Embed(
            title=f"Last {len(rows)} Entries",
            description="\n".join(lines),
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        msg = str(e)[:500]
        await interaction.response.send_message(f"Error: {msg}", ephemeral=True)


@tree.command(name="toggle-ai", description="Enable or disable AI categorization")
async def toggle_ai(interaction: discord.Interaction):
    global ai_enabled
    ai_enabled = not ai_enabled
    status = "enabled" if ai_enabled else "disabled"
    await interaction.response.send_message(f"AI categorization {status}.", ephemeral=True)


@tree.command(name="diag", description="Test Google Sheets connection")
async def diag(interaction: discord.Interaction):
    try:
        from config import get_google_credentials
        try:
            creds = get_google_credentials()
            email = creds.get("client_email", "MISSING")
        except Exception as e:
            await interaction.response.send_message(f"Credentials error: {e}", ephemeral=True)
            return

        from google.auth.transport.requests import Request as AuthRequest
        from google.oauth2.service_account import Credentials
        import requests

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(creds, scopes=scopes)
        credentials.refresh(AuthRequest())

        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {credentials.token}"})
        resp = session.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}")
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("properties", {}).get("title", "?")
            await interaction.response.send_message(
                f"**Connected**\nSheet: {title}\nEmail: {email}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"**Cannot open sheet** (HTTP {resp.status_code})\n"
                f"Email: {email}\nSheet ID: {SHEET_ID}\n\n"
                f"1. Open {SHEET_URL}\n"
                f"2. Click Share\n"
                f"3. Add `{email}` as Editor\n"
                f"4. Verify API enabled:\n"
                f"   https://console.cloud.google.com/apis/library/sheets.googleapis.com",
                ephemeral=True,
            )
    except Exception as e:
        await interaction.response.send_message(f"Diagnostic error: {e}", ephemeral=True)
