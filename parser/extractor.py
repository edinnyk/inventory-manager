import re

IRREGULAR_PLURALS = {
    "mice": "mouse",
    "geese": "goose",
    "feet": "foot",
    "teeth": "tooth",
    "men": "man",
    "women": "woman",
    "children": "child",
    "people": "person",
}

QTY_PATTERN = re.compile(
    r"(?P<qty>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"(?:\s+(?:box|boxes|case|cases|pack|packs|bottle|bottles|can|cans|crate|crates)\s+of)?"
    r"\s+(?P<item>[a-zA-Z][a-zA-Z\s-]*)",
    re.IGNORECASE,
)

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

SEP_NORMALIZE = re.compile(r"\band\b|\bor\b|[;,]")


def _normalize_item(name: str) -> str:
    name = name.strip().lower()
    if name in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[name]
    if name.endswith("ies") and len(name) > 4:
        return name[:-3] + "y"
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def _parse_quantity(raw: str) -> int:
    raw = raw.strip().lower()
    if raw in WORD_NUMBERS:
        return WORD_NUMBERS[raw]
    if raw in ("a", "an"):
        return 1
    return int(raw)


def extract_items(text: str) -> list[tuple[str, int]]:
    text = SEP_NORMALIZE.sub(",", text)
    fragments = [f.strip() for f in text.split(",") if f.strip()]
    results = []
    for frag in fragments:
        for match in QTY_PATTERN.finditer(frag):
            item_name = _normalize_item(match.group("item"))
            quantity = _parse_quantity(match.group("qty"))
            results.append((item_name, quantity))
    return results
