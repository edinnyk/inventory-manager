import os

import discord

from bot.discord_bot import tree
from config import SHEET_ID
from parser.pairs import parse_pairs
from sheets.google_sheets import (
    add_product_row,
    add_variant_column,
    find_product_row,
    get_log,
    list_variants,
    log_entry,
    matrix_get,
    matrix_read_cell,
    matrix_write_cell,
    product_info,
    rename_variant_column,
)
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"


def _val(v: int) -> str:
    return f"+{v}" if v >= 0 else str(v)


async def _process_items(
    interaction: discord.Interaction,
    product: str,
    items_text: str,
    operation: str,
):
    await interaction.response.defer()
    try:
        pairs = parse_pairs(items_text)
        if not pairs:
            await interaction.followup.send(
                f"Couldn't parse any variant pairs from: `{items_text}`\n"
                f"Try: `/add {product} 3 maple 5 cherry`"
            )
            return

        product_row = find_product_row(product)
        if product_row is None:
            await interaction.followup.send(
                f"Product **{product}** not found.\n"
                f"Use `/add-product {product}` to create it first."
            )
            return

        variants = list_variants()
        var_lookup = {v.lower(): v for v in variants}

        lines = []
        errors = []
        for var_name, qty in pairs:
            actual = var_lookup.get(var_name.lower())
            if actual is None:
                errors.append(f"Variant **{var_name}** not found. Available: {', '.join(variants)}")
                continue

            current = matrix_read_cell(product, actual)

            if operation == "add":
                new_val = current + qty
                delta = qty
            elif operation == "sub":
                new_val = max(0, current - qty)
                delta = -(current - new_val)
            elif operation == "set":
                new_val = qty
                delta = new_val - current

            matrix_write_cell(product, actual, new_val)
            lines.append(f"**{actual}**: {current} → {new_val} ({_val(delta)})")

        if lines:
            notes = "; ".join(lines)
            total_delta = sum(
                qty for var_name, qty in pairs
                if var_lookup.get(var_name.lower()) is not None
            )
            log_entry(product, _val(total_delta), notes)

        embed = discord.Embed(
            title=f"{operation.title()} — {product}",
            color=discord.Color.green(),
        )
        if lines:
            embed.description = "\n".join(lines)
        if errors:
            embed.add_field(name="Errors", value="\n".join(errors), inline=False)

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(str(e))
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="add", description="Add quantity to product variants")
async def add(interaction: discord.Interaction, product: str, items: str):
    await _process_items(interaction, product, items, "add")


@tree.command(name="sub", description="Subtract quantity from product variants")
async def sub(interaction: discord.Interaction, product: str, items: str):
    await _process_items(interaction, product, items, "sub")


@tree.command(name="set", description="Set exact quantity for product variants")
async def set_(interaction: discord.Interaction, product: str, items: str):
    await _process_items(interaction, product, items, "set")


@tree.command(name="stock", description="Show current totals for a product")
async def stock(interaction: discord.Interaction, product: str):
    await interaction.response.defer()
    try:
        info = product_info(product)
        data = matrix_get(product)

        title = f"Stock — {info['product']}"
        summary = []
        if info["size"]:
            summary.append(f"**Size**: {info['size']}")
        if info["carcass"]:
            summary.append(f"**Carcass**: {info['carcass']}")
        if summary:
            title += " | " + " | ".join(summary)

        if not data:
            await interaction.followup.send(f"No variants found for **{info['product']}**.")
            return
        lines = [f"**{var}**: {qty}" for var, qty in sorted(data.items())]
        embed = discord.Embed(
            title=title,
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=SHEET_URL)
        await interaction.followup.send(embed=embed)
    except ValueError as e:
        await interaction.followup.send(str(e))
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="log", description="Show recent audit log entries for a product")
async def log(interaction: discord.Interaction, product: str, n: int = 5):
    await interaction.response.defer()
    try:
        entries = get_log(product, n)
        if not entries:
            await interaction.followup.send(f"No log entries for **{product}**.")
            return
        lines = [
            f"**{e['date']}** | {e['delta']} — {e['notes']}"
            for e in entries
        ]
        embed = discord.Embed(
            title=f"Log — {product} (last {len(entries)})",
            description="\n".join(lines),
            color=discord.Color.purple(),
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="add-product", description="Add a new product to the inventory matrix")
async def add_product(interaction: discord.Interaction, product: str, size: str = ""):
    await interaction.response.defer()
    try:
        existing = find_product_row(product)
        if existing is not None:
            await interaction.followup.send(f"Product **{product}** already exists at row {existing}.")
            return
        add_product_row(product, size)
        log_entry(product, "0", "Product added")
        await interaction.followup.send(f"Product **{product}** added{ ' (size: ' + size + ')' if size else ''}.")
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="add-variant", description="Add a new variant column to the inventory matrix")
async def add_variant(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    try:
        add_variant_column(name)
        await interaction.followup.send(f"Variant **{name}** added as a new column.")
    except ValueError as e:
        await interaction.followup.send(str(e))
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="rename-variant", description="Rename a variant column")
async def rename_variant(interaction: discord.Interaction, old: str, new: str):
    await interaction.response.defer()
    try:
        rename_variant_column(old, new)
        await interaction.followup.send(f"Variant **{old}** renamed to **{new}**.")
    except ValueError as e:
        await interaction.followup.send(str(e))
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)[:500]}")


@tree.command(name="sheet", description="Get the Google Sheet link")
async def sheet(interaction: discord.Interaction):
    await interaction.response.send_message(SHEET_URL)


@tree.command(name="version", description="Show the deployed git commit hash")
async def version(interaction: discord.Interaction):
    commit = os.getenv("RAILWAY_GIT_COMMIT", "unknown (local dev)")
    await interaction.response.send_message(f"Commit: `{commit}`", ephemeral=True)
