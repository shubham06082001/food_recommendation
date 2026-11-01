from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException

from .database import get_db

MEAL_PERIODS = ["breakfast", "snacks", "lunch", "dinner"]
HEALTHY_TAGS = ["high_protein", "high_fibre", "balanced", "lower_sodium"]
ORDER_STATUSES = ["confirmed", "preparing", "ready", "collected", "cancelled"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today() -> str:
    return date.today().isoformat()


def pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def serialize(document: dict[str, Any]) -> dict[str, Any]:
    document = {**document}
    document.pop("_id", None)
    for key, value in document.items():
        if isinstance(value, datetime):
            document[key] = value.isoformat()
    return document


def current_user(x_user_id: str | None = Header(default=None)) -> dict[str, Any]:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Login required")
    user = get_db().users.find_one({"user_id": x_user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def require_manager(user: dict = Depends(current_user)) -> dict[str, Any]:
    if user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return user


def require_self_or_manager(user_id: str, user: dict[str, Any]) -> None:
    if user["user_id"] != user_id and user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not allowed")


def stock_status(item: dict[str, Any]) -> str:
    quantity = float(item.get("quantity", 0))
    if quantity <= 0:
        return "STOCKOUT"
    if quantity <= float(item.get("reorder_point", 0)):
        return "CRITICAL"
    return "HEALTHY"


def record_movement(db: Any, ingredient_id: str, kind: str, quantity: float, user_id: str, **extra: Any) -> None:
    """Append an inventory movement; quantity is signed (negative = consumption)."""
    db.inventory_movements.insert_one({
        "movement_id": uuid4().hex, "ingredient_id": ingredient_id, "type": kind,
        "quantity": quantity, "user_id": user_id, "created_at": now_utc(), **extra,
    })


# Diets each dietary preference may eat; recipes carry one of veg / egg / non_veg.
DIET_ALLOWED = {
    "vegetarian": {"veg"},
    "vegan": {"veg"},
    "eggetarian": {"veg", "egg"},
    "non_vegetarian": {"veg", "egg", "non_veg"},
    "no_preference": {"veg", "egg", "non_veg"},
}
VEGAN_EXCLUDED_ALLERGENS = {"milk", "dairy", "egg"}


def nutrition_tags(protein_g: float, fibre_g: float, sodium_mg: float, energy_kcal: float) -> list[str]:
    tags = []
    if protein_g >= 12:
        tags.append("high_protein")
    if fibre_g >= 5:
        tags.append("high_fibre")
    if 0 < sodium_mg <= 300:
        tags.append("lower_sodium")
    if protein_g >= 7 and fibre_g >= 3 and energy_kcal <= 550:
        tags.append("balanced")
    return tags


def eligibility(recipe: dict[str, Any], preferences: dict[str, Any]) -> tuple[bool, str]:
    """Check a recipe against a user's dietary preference and declared allergen exclusions."""
    diet = preferences.get("dietary_preference") or "no_preference"
    if recipe.get("diet", "veg") not in DIET_ALLOWED.get(diet, DIET_ALLOWED["no_preference"]):
        return False, f"Not {diet.replace('_', ' ')}"
    allergens = {a.lower() for a in recipe.get("declared_allergens", [])}
    if diet == "vegan" and allergens & VEGAN_EXCLUDED_ALLERGENS:
        return False, "Contains animal products"
    blocked = allergens & {a.lower() for a in preferences.get("declared_allergens", [])}
    if blocked:
        return False, f"Contains {', '.join(sorted(blocked))}"
    return True, ""


def current_meal_period(hour: int) -> str:
    if hour < 11:
        return "breakfast"
    if hour < 15:
        return "lunch"
    if hour < 18:
        return "snacks"
    return "dinner"
