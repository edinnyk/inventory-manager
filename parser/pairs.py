import re

PAIR_RE = re.compile(
    r"(?:"
    r"(?P<qty1>\d+)\s*(?:x\s*)?(?P<var1>[a-zA-Z][a-zA-Z\s/&-]*)"
    r"|"
    r"(?P<var2>[a-zA-Z][a-zA-Z\s/&-]*?)\s*:\s*(?P<qty2>\d+)"
    r"|"
    r"(?P<var3>[a-zA-Z][a-zA-Z\s/&-]*?)\s+(?P<qty3>\d+)"
    r")",
    re.IGNORECASE,
)

SEPARATORS = re.compile(r"\s*(?:,|\band\b|&)\s*")


def parse_pairs(text: str) -> list[tuple[str, int]]:
    seen = set()
    result = []
    for segment in SEPARATORS.split(text):
        segment = segment.strip()
        if not segment:
            continue
        for m in PAIR_RE.finditer(segment):
            if m.group("qty1"):
                var = m.group("var1").strip()
                qty = int(m.group("qty1"))
            elif m.group("qty2"):
                var = m.group("var2").strip()
                qty = int(m.group("qty2"))
            elif m.group("qty3"):
                var = m.group("var3").strip()
                qty = int(m.group("qty3"))
            else:
                continue
            if var.lower() not in seen:
                seen.add(var.lower())
                result.append((var, qty))
    return result
