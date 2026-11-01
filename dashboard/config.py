"""Navigation structure and small shared constants for the ECOS dashboard."""

from __future__ import annotations

# (view, Material icon) per role; the first item is the landing page.
ROLE_NAV = {
    "employee": [
        ("Home", ":material/home:"),
        ("Menu", ":material/restaurant_menu:"),
        ("My orders", ":material/receipt_long:"),
        ("My wellness", ":material/monitor_heart:"),
        ("Profile", ":material/settings:"),
    ],
    "manager": [
        ("Today", ":material/dashboard:"),
        ("Live orders", ":material/receipt_long:"),
        ("Inventory", ":material/inventory_2:"),
        ("Menu management", ":material/menu_book:"),
        ("Forecasting", ":material/insights:"),
        ("Executive", ":material/query_stats:"),
        ("Copilot", ":material/smart_toy:"),
    ],
}
ROLE_LANDING = {role: items[0][0] for role, items in ROLE_NAV.items()}
MEAL_PERIODS = ["breakfast", "lunch", "snacks", "dinner"]
ORDER_STATUSES = ["confirmed", "preparing", "ready", "collected", "cancelled"]
NEXT_STATUS = {"confirmed": "preparing", "preparing": "ready", "ready": "collected"}
TAG_LABELS = {"high_protein": "High protein", "high_fibre": "High fibre",
              "lower_sodium": "Lower sodium", "balanced": "Balanced"}
DIET_OPTIONS = {"no_preference": "No preference", "vegetarian": "Vegetarian", "vegan": "Vegan",
                "eggetarian": "Eggetarian", "non_vegetarian": "Non-vegetarian"}
ALLERGEN_OPTIONS = ["milk", "egg", "wheat", "gluten", "peanut", "tree nuts", "soy", "mustard", "fish", "sesame"]
STATUS_BADGE = {"HEALTHY": ":green-badge[Healthy]", "CRITICAL": ":orange-badge[Critical]",
                "STOCKOUT": ":red-badge[Stockout]"}
DISCLAIMER = ("Nutrition values are estimates. Allergen information reflects declared recipe evidence "
              "and is not a cross-contact safety guarantee.")
