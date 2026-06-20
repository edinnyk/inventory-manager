from parser.ai_categorizer import ai_categorize
from parser.categories import get_category


def categorize_items(
    items: list[tuple[str, int]],
    use_ai: bool = False,
    custom_categories: dict[str, list[str]] | None = None,
) -> list[tuple[str, str, int]]:
    result = []
    for item_name, quantity in items:
        category = get_category(item_name, custom_categories)
        if category == "Uncategorized" and use_ai:
            ai_cat = ai_categorize(item_name)
            if ai_cat:
                category = ai_cat
        result.append((item_name, category, quantity))
    return result
