from datetime import datetime

import discord

from bot.discord_bot import tree
from config import SHEET_ID
from parser.categorizer import categorize_items
from parser.categories import DEFAULT_CATEGORIES
from parser.extractor import extract_items
from sheets.google_sheets import append_entry, get_recent

custom_categories: dict[str, list[str]] = {}
ai_enabled = False

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"


@tree.command(name="inv", description="Add items to inventory")
async def inv(interaction: discord.Interaction, items: str):
    await interaction.response.defer()

    parsed = extract_items(items)
    if not parsed:
        await interaction.followup.send("Couldn't parse any items. Try: `/inv 5 laptops and 3 chairs`")
        return

    categorized = categorize_items(parsed, use_ai=ai_enabled, custom_categories=custom_categories)

    lines = []
    for item_name, category, quantity in categorized:
        append_entry(item_name, category, quantity)
        lines.append(f"**{item_name}** — {quantity} ({category})")

    embed = discord.Embed(
        title="Inventory Added",
        description="\n".join(lines),
        color=discord.Color.green(),
        timestamp=datetime.now(),
    )
    embed.set_footer(text=f"View sheet: {SHEET_URL}")
    await interaction.followup.send(embed=embed)


@tree.command(name="categories", description="List all categories and their keywords")
async def categories(interaction: discord.Interaction):
    all_cats = {**DEFAULT_CATEGORIES, **custom_categories}
    lines = []
    for cat, keywords in sorted(all_cats.items()):
        kw = ", ".join(sorted(set(keywords)))
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


@tree.command(name="sheet", description="Get the Google Sheet link")
async def sheet(interaction: discord.Interaction):
    await interaction.response.send_message(SHEET_URL)


@tree.command(name="recent", description="Show recent inventory entries")
async def recent(interaction: discord.Interaction, n: int = 5):
    rows = get_recent(n)
    if not rows:
        await interaction.response.send_message("No entries yet.")
        return

    lines = []
    for row in reversed(rows):
        padded = row + [""] * (6 - len(row))
        lines.append(f"**{padded[0]}** | {padded[2]}x {padded[1]} — {padded[3]}")

    embed = discord.Embed(
        title=f"Last {len(rows)} Entries",
        description="\n".join(lines),
        color=discord.Color.purple(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="toggle-ai", description="Enable or disable AI categorization")
async def toggle_ai(interaction: discord.Interaction):
    global ai_enabled
    ai_enabled = not ai_enabled
    status = "enabled" if ai_enabled else "disabled"
    await interaction.response.send_message(f"AI categorization {status}.", ephemeral=True)
