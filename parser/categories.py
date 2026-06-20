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
        "saw", "saw", "ladder", "ladders", "measuring tape", "level",
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


def get_category(item_name: str, custom_categories: dict[str, list[str]] | None = None) -> str:
    name = item_name.lower()
    all_categories = {**DEFAULT_CATEGORIES, **(custom_categories or {})}
    for category, keywords in all_categories.items():
        for keyword in keywords:
            if keyword in name:
                return category
    return "Uncategorized"
