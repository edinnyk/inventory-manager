# v3 — Action Plan (implemented Jun 23 2026)

All 4 issues in this plan have been implemented. See the git diff for the
exact changes, or PROBLEM_LOG.md for the narrative.

## Overview

Addressed 4 issues on top of the working v2 codebase:

1. **CARCASS column support** — column D is treated as data, not variant
2. **Spacer column (E)** — skipped by bot, variants start at F
3. **Auto-capitalization** — all written values are upper-cased
4. **Parameter rename** — "pairs" → "items"
5. **Adaptable layout** — bot reads row 1 to discover structure

Changes were additive to the current v2 files — no structural rewrite.

---

## Issue 1: CARCASS Column + Spacer + Variant Detection

### Current behavior

| Column | Content | Bot sees |
|--------|---------|----------|
| B | Product ID | Yes (find_product_row) |
| C | SIZE | Ignored |
| D | CARCASS | Ignored |
| E | (spacer) | **Treated as variant #1** |
| F | MAPLE | Treated as variant |
| G | CHERRY | Treated as variant |

`find_variant_col()` scans `E1:ZZ1` → Column E is treated as the first variant.

### Desired behavior

| Column | Content | Bot sees |
|--------|---------|----------|
| B | Product ID | Yes |
| C | SIZE | Ignored |
| D | CARCASS | Displayed in /stock output |
| E | (spacer) | **Skipped — not a variant** |
| F | MAPLE | Treated as variant #1 |
| G | CHERRY | Treated as variant |

### Changes needed

**`sheets/schema.py`** — add known non-variant headers:
```python
HEADERS = ["Item", "Quantity", "Date", "Notes"]
NON_VARIANT_HEADERS = {"size", "carcass", ""}  # lowercase for matching
```

**`sheets/google_sheets.py`** — update variant detection:

`find_variant_col()` and `list_variants()`:
- Read row 1 from column A onwards
- Skip any column whose header is in `NON_VARIANT_HEADERS`
- Return only the variant columns

`_variant_start_col()` — new helper:
```python
def _variant_start_col(session, sheet_name) -> int:
    """Find the first column after all non-variant headers + spacers"""
    range_ = _range(sheet_name, "A1:ZZ1")
    resp = session.get(...)
    headers = resp.json().get("values", [[]])[0]
    for i, h in enumerate(headers):
        if h and str(h).strip().lower() not in NON_VARIANT_HEADERS:
            return i + 1  # 1-indexed column number
    return 6  # fallback to F (column 6)
```

`carcass_col()` — new function:
```python
def product_carcass(product: str) -> str:
    """Read the CARCASS value for a product"""
    row = find_product_row(product)
    # Column D = index 4 (1-indexed)
    range_ = _range(sheet_name, "D{row}")
    ...
```

`matrix_get()` — include carcass in the returned dict:
```python
result["__carcass__"] = carcass_value
```

### How it looks in /stock output
```
Product: BPP09
CARCASS: 16
MAPLE: 13
CHERRY: 3
```

---

## Issue 2: Auto-Capitalization

### Current behavior
```
/add BPP09 3 maple
  → cell reads "maple" (lowercase)
```

### Desired behavior
```
/add BPP09 3 maple
  → cell reads "MAPLE" (uppercase)
```

### Changes needed

**`sheets/google_sheets.py`** — add a helper and use it in write functions:

```python
def _cap(val: str) -> str:
    return val.upper().strip()
```

Apply in:
- `add_product_row()` — capitalize `product` before writing
- `add_variant_column()` — capitalize `name` before writing
- `matrix_write_cell()` — capitalize the value before writing

**Note:** Only affects newly written values. Existing sheet data is not retroactively changed.

---

## Issue 3: Parameter Rename

### Current
```
/add product: BPP09 pairs: 3 maple 5 cherry
```

### Options
| Name | Discord prompt looks like | Clarity |
|------|--------------------------|---------|
| `items` | `/add product: BPP09 items: 3 maple 5 cherry` | Natural — "items" = what's being added |
| `stock` | `/add product: BPP09 stock: 3 maple 5 cherry` | OK — "stock" is what's changing |
| `quantities` | `/add product: BPP09 quantities: 3 maple 5 cherry` | Accurate but wordy |
| `values` | `/add product: BPP09 values: 3 maple 5 cherry` | Vague |

### My recommendation
`items` — most natural English. "add 3 maple 5 cherry items to BPP09" reads correctly.

### Changes needed
- `bot/handlers.py` — rename parameter in `@tree.command(name="add", ...)`, `sub`, `set`
- Update `_process_pairs()` parameter name to match
- Update all error messages that reference "pairs"

---

## Issue 4: Adaptable Layout (Phase 1)

### Core idea
Instead of hardcoding "variants start at E", scan row 1 and figure out the layout dynamically.

### Algorithm
```
1. Read row 1, columns A through ZZ
2. For each cell in row 1:
   a. If cell is empty → skip (it's a spacer)
   b. If cell.lower() in NON_VARIANT_HEADERS → skip (it's a known non-variant)
   c. Otherwise → it's a variant
3. Return the list of variant column indices
```

### Why this works
- If user adds a new column between SIZE and CARCASS → it's a spacer unless it has a known header → if it has a known header name it's skipped → if it has an unknown header it's treated as a variant
- If user renames "CARCASS" → needs to be added to NON_VARIANT_HEADERS, or use Phase 2

### Phase 2 (future)
Add `/layout` command:
```
/layout carcass: D spacer: E
```
Stored in a dict in `handlers.py` (like `custom_categories` was). Lets the user define which columns are which without editing code.

---

## Files to Change

| File | Changes |
|------|---------|
| `sheets/schema.py` | Add `NON_VARIANT_HEADERS` set |
| `sheets/google_sheets.py` | `find_variant_col()`, `list_variants()`, `matrix_get()`, `add_variant_column()` — use dynamic column detection. Add `_cap()` helper. Add `product_carcass()` if needed. |
| `bot/handlers.py` | Rename `pairs` → `items`. Update error messages. Add carcass to `/stock` output. |

---

## Order of Implementation

1. **Parameter rename** — simplest, just text changes in handlers.py
2. **Auto-capitalization** — small, additive helper function
3. **Variant detection + CARCASS** — the main logic change
4. **Phase 2 `/layout` command** — only if needed
