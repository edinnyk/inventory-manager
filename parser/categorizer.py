from parser.ai_categorizer import ai_categorize
from parser.categories import get_category, get_subcategory


def categorize_items(
    items: list[tuple[str, int]],
    use_ai: bool = False,
    custom_categories: dict[str, list[str]] | None = None,
    custom_subcategories: dict[str, dict[str, list[str]]] | None = None,
) -> list[tuple[str, str, str, int]]:
    result = []
    for item_name, quantity in items:
        category = get_category(item_name, custom_categories)
        subcategory = ""
        if category != "Uncategorized":
            subcategory = get_subcategory(item_name, category, custom_subcategories)
        if category == "Uncategorized" and use_ai:
            ai_cat = ai_categorize(item_name)
            if ai_cat:
                category = ai_cat
        result.append((item_name, category, subcategory, quantity))
    return result
