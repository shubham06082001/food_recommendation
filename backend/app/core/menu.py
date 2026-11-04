import re
from collections import defaultdict
from typing import Any

from pymongo.collation import Collation

from .common import serialize

# Catalog dishes have no ingredient lines, so their stock is not tracked and they are always orderable.
UNTRACKED_PORTIONS = 99
_UNITS = {"g": ("mass", 1), "kg": ("mass", 1000), "ml": ("volume", 1), "l": ("volume", 1000)}
_BY_NAME = Collation(locale="en", strength=2)


def stock_map(db: Any) -> dict[str, dict[str, Any]]:
    return {item["ingredient_id"]: item for item in db.ingredients.find({}, {"_id": 0})}


def _base(quantity: Any, unit: str | None) -> tuple[str, float]:
    unit = (unit or "").lower()
    group, factor = _UNITS.get(unit, (unit, 1))
    return group, float(quantity) * factor


def per_portion_needs(recipe: dict[str, Any], stock: dict[str, dict[str, Any]]) -> dict[str, float] | None:
    """Stock units needed per portion, repeated lines summed; None if a line is missing, zero or in an incompatible unit."""
    needs: dict[str, float] = defaultdict(float)
    for line in recipe.get("ingredients") or []:
        item = stock.get(line["ingredient_id"])
        if not item or float(line.get("quantity", 0)) <= 0:
            return None
        group, amount = _base(line["quantity"], line.get("unit") or item.get("unit"))
        stock_group, unit_size = _base(1, item.get("unit"))
        if group != stock_group:
            return None
        needs[line["ingredient_id"]] += amount / unit_size
    return needs


def max_portions(recipe: dict[str, Any], stock: dict[str, dict[str, Any]]) -> int:
    if not recipe.get("ingredients"):
        return UNTRACKED_PORTIONS
    needs = per_portion_needs(recipe, stock)
    if not needs:
        return 0
    # Plain `//` on floats under-counts (1 // 0.1 == 9.0), hence the small tolerance.
    return min(int(float(stock[i].get("quantity", 0)) / n + 1e-9) for i, n in needs.items())


def menu_filter(meal_period: str | None = None, text: str = "", dish_ids: Any = None) -> dict[str, Any]:
    """A recipe is on the menu unless a manager excluded it; `meal_periods` says when it is served."""
    query: dict[str, Any] = {"on_menu": {"$ne": False}}
    if meal_period:
        query["meal_periods"] = meal_period
    if dish_ids is not None:
        query["dish_id"] = {"$in": list(dish_ids)}
    if text.strip():
        query["name"] = {"$regex": re.escape(text.strip()), "$options": "i"}
    return query


def menu_count(db: Any, meal_period: str | None = None, text: str = "") -> int:
    return db.recipes.count_documents(menu_filter(meal_period, text))


def menu_items(db: Any, meal_period: str | None = None, *, dish_ids: Any = None, text: str = "",
               light: bool = False, skip: int = 0, limit: int = 0) -> list[dict[str, Any]]:
    """Orderable menu with live availability. `light` drops the heavy nutrient profile (used for ranking)."""
    cursor = db.recipes.find(menu_filter(meal_period, text, dish_ids), {"_id": 0, **({"nutrient_profile": 0} if light else {})})
    cursor = cursor.collation(_BY_NAME).sort("name", 1).skip(skip).limit(limit)
    stock = stock_map(db)
    items = []
    for recipe in cursor:
        portions = max_portions(recipe, stock)
        reason = ""
        if recipe.get("evidence_status", "confirmed") != "confirmed":
            reason = "Recipe evidence under review"
        elif portions <= 0:
            reason = "Ingredients out of stock"
        items.append({**serialize(recipe), "meal_period": meal_period or recipe["meal_periods"][0],
                      "available": not reason, "unavailable_reason": reason, "maximum_portions": portions,
                      "stock_tracked": bool(recipe.get("ingredients"))})
    return items
