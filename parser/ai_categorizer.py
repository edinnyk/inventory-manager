from config import OPENAI_API_KEY

CATEGORIES_LIST = [
    "Electronics", "Furniture", "Office Supplies", "Food & Beverage",
    "Clothing", "Tools", "Cleaning", "Medical", "Packaging",
]


def ai_categorize(item_name: str) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            f"Categorize this inventory item into exactly one category from the list below. "
            f"Respond with only the category name, nothing else.\n\n"
            f"Categories: {', '.join(CATEGORIES_LIST)}\n"
            f"Item: {item_name}"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )
        category = response.choices[0].message.content.strip()
        if category in CATEGORIES_LIST:
            return category
    except Exception:
        pass
    return None
