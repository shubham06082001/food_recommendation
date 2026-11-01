from typing import Any

from .common import serialize, today


def stock_map(db: Any) -> dict[str, dict[str, Any]]:
    return {item["ingredient_id"]: item for item in db.ingredients.find({}, {"_id": 0})}


def max_portions(recipe: dict[str, Any], stock: dict[str, dict[str, Any]]) -> int:
    """Portions the current stock supports; 0 when any ingredient is missing."""
    limits = []
    for line in recipe.get("ingredients", []):
        item = stock.get(line["ingredient_id"])
        per_portion = float(line.get("quantity", 0))
        if not item or per_portion <= 0:
            return 0
        limits.append(int(float(item.get("quantity", 0)) // per_portion))
    return min(limits) if limits else 0


def menu_items(db: Any, meal_period: str | None = None, date: str | None = None) -> list[dict[str, Any]]:
    """Published menu items for a date with live availability, one entry per menu/dish pair."""
    date = date or today()
    if date == today() and not db.menus.find_one({"date": date}):
        from .seed import ensure_menus  # pylint: disable=import-outside-toplevel
        ensure_menus(db, date)
    query: dict[str, Any] = {"date": date, "published": True}
    if meal_period:
        query["meal_period"] = meal_period
    menus = list(db.menus.find(query))
    dish_ids = {dish_id for menu in menus for dish_id in menu.get("dish_ids", [])}
    recipes = {r["dish_id"]: r for r in db.recipes.find({"dish_id": {"$in": list(dish_ids)}})}
    stock = stock_map(db)
    items = []
    for menu in menus:
        paused = set(menu.get("paused_dish_ids", []))
        for dish_id in menu.get("dish_ids", []):
            recipe = recipes.get(dish_id)
            if not recipe:
                continue
            portions = max_portions(recipe, stock)
            reason = ""
            if recipe.get("evidence_status", "confirmed") != "confirmed":
                reason = "Recipe evidence under review"
            elif dish_id in paused:
                reason = "Paused by manager"
            elif portions <= 0:
                reason = "Ingredients out of stock"
            items.append({
                **serialize(recipe),
                "menu_id": menu["menu_id"],
                "meal_period": menu["meal_period"],
                "available": not reason,
                "unavailable_reason": reason,
                "maximum_portions": portions,
            })
    return items
