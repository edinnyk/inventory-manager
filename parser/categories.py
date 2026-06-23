DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Electronics": [
        "laptop", "laptops", "computer", "computers", "monitor", "monitors",
        "mouse", "mice", "keyboard", "keyboards", "phone", "phones",
        "tablet", "tablets", "printer", "printers", "cable", "cables",
        "charger", "chargers", "battery", "batteries", "headphone", "headphones",
        "speaker", "speakers", "webcam", "camera", "cameras", "router",
        "hard drive", "ssd", "usb", "flash drive",
    ],
    "Furniture": [
        "chair", "chairs", "desk", "desks", "table", "tables",
        "cabinet", "cabinets", "shelf", "shelves", "drawer", "drawers",
        "sofa", "couch", "bed", "beds", "stool", "stools",
        "bookcase", "bookcases", "filing cabinet", "bench",
    ],
    "Office Supplies": [
        "paper", "pen", "pens", "pencil", "pencils", "marker", "markers",
        "stapler", "staplers", "tape", "scissors", "folder", "folders",
        "binder", "binders", "notebook", "notebooks", "envelope", "envelopes",
        "sticky note", "post-it", "clip", "clips", "rubber band",
    ],
    "Food & Beverage": [
        "water", "soda", "snack", "snacks", "coffee", "tea",
        "cereal", "rice", "pasta", "oil", "sauce", "canned",
        "flour", "sugar", "salt", "spice", "spices", "bread",
        "milk", "juice", "beer", "wine", "fruit", "vegetable",
    ],
    "Clothing": [
        "shirt", "shirts", "pants", "jeans", "jacket", "jackets",
        "shoe", "shoes", "sock", "socks", "hat", "hats",
        "uniform", "uniforms", "glove", "gloves", "apron", "vest",
        "coat", "coats", "belt", "belts", "tie", "ties",
    ],
    "Tools": [
        "hammer", "screwdriver", "wrench", "pliers", "drill", "drills",
        "saw", "ladder", "ladders", "measuring tape", "level",
        "flashlight", "knife", "knives", "glue", "paint", "brush",
    ],
    "Cleaning": [
        "soap", "detergent", "bleach", "cleaner", "disinfectant",
        "sponge", "sponges", "towel", "towels", "mop", "broom",
        "trash bag", "garbage bag", "glove", "wipes",
    ],
    "Medical": [
        "mask", "masks", "glove", "gloves", "bandage", "bandages",
        "thermometer", "medicine", "pill", "pills", "first aid",
        "sanitizer", "syringe", "vaccine",
    ],
    "Packaging": [
        "box", "boxes", "bag", "bags", "wrap", "label", "labels",
        "tape", "bubble wrap", "foam", "pallet", "pallets",
        "container", "containers", "bottle", "bottles", "jar", "jars",
    ],
}

SUBCATEGORIES: dict[str, dict[str, list[str]]] = {
    "Electronics": {
        "Computers": ["laptop", "laptops", "computer", "computers", "desktop", "workstation", "notebook"],
        "Peripherals": ["mouse", "mice", "keyboard", "keyboards", "monitor", "monitors", "webcam", "speaker", "speakers", "headphone", "headphones"],
        "Cables & Chargers": ["cable", "cables", "charger", "chargers", "adapter", "usb", "hdmi"],
        "Phones & Tablets": ["phone", "phones", "tablet", "tablets", "smartphone"],
        "Printers & Scanners": ["printer", "printers", "scanner"],
    },
    "Furniture": {
        "Seating": ["chair", "chairs", "stool", "stools", "sofa", "couch", "bench"],
        "Desks & Tables": ["desk", "desks", "table", "tables"],
        "Storage": ["cabinet", "cabinets", "shelf", "shelves", "drawer", "drawers", "bookcase", "bookcases", "filing cabinet"],
        "Beds": ["bed", "beds", "mattress"],
    },
    "Office Supplies": {
        "Paper & Notebooks": ["paper", "notebook", "notebooks", "envelope", "envelopes", "sticky note", "post-it"],
        "Writing": ["pen", "pens", "pencil", "pencils", "marker", "markers"],
        "Fasteners": ["stapler", "staplers", "clip", "clips", "rubber band", "binder", "binders"],
        "Cutting": ["scissors", "cutter", "knife"],
    },
    "Clothing": {
        "Tops": ["shirt", "shirts", "jacket", "jackets", "vest", "coat", "coats", "uniform", "uniforms"],
        "Bottoms": ["pants", "jeans", "belt", "belts", "apron"],
        "Footwear": ["shoe", "shoes", "sock", "socks"],
        "Headwear": ["hat", "hats", "cap"],
    },
}


def get_category(item_name: str, custom_categories: dict[str, list[str]] | None = None) -> str:
    name = item_name.lower()
    all_categories = {**DEFAULT_CATEGORIES, **(custom_categories or {})}
    for category, keywords in all_categories.items():
        for keyword in keywords:
            if keyword in name:
                return category
    return "Uncategorized"


def get_subcategory(
    item_name: str,
    category: str,
    custom_subcategories: dict[str, dict[str, list[str]]] | None = None,
) -> str:
    name = item_name.lower()
    all_subcats: dict[str, list[str]] = {}
    if category in SUBCATEGORIES:
        all_subcats.update(SUBCATEGORIES[category])
    if custom_subcategories and category in custom_subcategories:
        for subcat, keywords in custom_subcategories[category].items():
            if subcat in all_subcats:
                all_subcats[subcat].extend(keywords)
            else:
                all_subcats[subcat] = keywords
    for subcat, keywords in all_subcats.items():
        for keyword in keywords:
            if keyword in name:
                return subcat
    return ""


def all_keywords(custom_categories: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    return {**DEFAULT_CATEGORIES, **(custom_categories or {})}


def all_subcategories(
    custom_subcategories: dict[str, dict[str, list[str]]] | None = None,
) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for cat, subs in SUBCATEGORIES.items():
        result[cat] = dict(subs)
    if custom_subcategories:
        for cat, subs in custom_subcategories.items():
            if cat in result:
                for sub, kw in subs.items():
                    if sub in result[cat]:
                        result[cat][sub].extend(kw)
                    else:
                        result[cat][sub] = kw
            else:
                result[cat] = dict(subs)
    return result
