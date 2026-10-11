"""Workspace organization labels; categories never change tool permissions."""
DEFAULT_CATEGORIES = [
    {"id": "hr", "name": "HR & policy", "color": "#47d7d0", "built_in": True},
    {"id": "finance", "name": "Finance", "color": "#9b8cff", "built_in": True},
    {"id": "support", "name": "Customer support", "color": "#88b7ef", "built_in": True},
    {"id": "security", "name": "Security", "color": "#f2b866", "built_in": True},
    {"id": "optimizer", "name": "Optimizer", "color": "#a8d390", "built_in": True},
    {"id": "custom", "name": "Other", "color": "#86b9e4", "built_in": True},
]
ROLE_CATEGORIES = {category["id"]: category["id"] for category in DEFAULT_CATEGORIES}


def fallback_category(role):
    return ROLE_CATEGORIES.get(role, "custom")


def normalized_name(name):
    return " ".join(name.split()).casefold()
