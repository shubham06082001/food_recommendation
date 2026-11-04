"""Operational recipes are synced from the Qdrant `food_nutrients` catalog.

The catalog owns what a dish IS (name, diet, allergens, nutrition). Managers own how it is SERVED (on_menu, price,
meal periods, optional stock lines); those are written only when a dish is first created, so re-syncing never
overwrites a manager's choice. Recipes a manager authored (uploads, legacy) are never touched by the sync.
"""

import logging
import re
import threading
from datetime import timedelta
from typing import Any

from pymongo import UpdateOne

from . import vectors
from .common import now_utc, nutrition_tags
from .config import settings
from .enrich import MACROS, MICROS, build_profile, enrich_in_background
from .semantic import COLLECTION

logger = logging.getLogger(__name__)
_lock = threading.Lock()
RETRY_SECONDS = 60
CATALOG_VERSION = 2  # Bump when the mapping changes: existing databases then re-sync once.

NUTRIENT_KEYS = [k for k in {**MACROS, **MICROS} if k != "vitd_ug"] + ["vitd2_ug", "vitd3_ug"]
SERVING_KEYS = [f"unit_serving_{k}" for k in NUTRIENT_KEYS]
FIELDS = ["food_code", "food_name", "alias_name", "food_preference", "allergens", "ingredients", "servings_unit",
          *NUTRIENT_KEYS, *SERVING_KEYS]
MAX_PORTION_KCAL = 900  # Larger catalog 'servings' are whole-recipe quantities, not one cafeteria portion.
FALLBACK_PORTION_G = 250

MEAT = re.compile(r"\b(?:chicken|mutton|lamb|beef|pork|bacon|ham|fish|prawns?|shrimps?|crab|lobster|keema|meat|"
                  r"sausages?|salami|turkey|veal|tuna|salmon|squid|duck|goat|hamburger)\b")
EGG = re.compile(r"\b(?:eggs?|omelett?e|omlet|anda)\b")
# Ingredients/components (stock, sauce, dough...) stay on the menu but are not suggested unless searched for.
COMPONENT = re.compile(r"\b(?:stock|sauce|puree|chutney|pickle|achaar|icing|dressing|paste|baghar|tadka|gravy|dough|crust|"
                       r"syrup|jam|seasoning|marinade|glaze|dip|(?:garam|chaat|pav bhaji|sambhar|sambar) masala|masala (?:powder|mix))\b")
RANK = {"veg": 0, "egg": 1, "non_veg": 2}
LABELS = {"veg": "veg", "jain_food": "veg", "egg": "egg", "non_veg": "non_veg"}

# First matching rule wins; anything unmatched is a main course.
PERIOD_RULES = [
    (r"idli|dosa|uttapam|upma|poha|porridge|dalia|oats|cornflakes|muesli|toast|omelett?e|omlet|pancake|chilla|thepla|"
     r"pongal|appam|puttu|boiled egg|bhurji", ["breakfast"]),
    (r"sandwich|paratha|parantha", ["breakfast", "snacks"]),
    (r"pakora|pakoda|samosa|chaat|tikki|cutlet|rolls?|biscuits?|cookies?|cake|pastry|ladoo|burfi|halwa|kheer|pudding|"
     r"ice cream|juice|shake|lassi|buttermilk|tea|coffee|kebab|bhujia|chiwda|dhokla|popcorn|nuggets?|fries|sharbat|"
     r"squash|smoothie|payasam|rasmalai|jalebi|gulab jamun|chikki|mathri|namkeen|puff|tart|pie|muffin|brownie|candy|"
     r"chocolate|soup|salad|raita", ["snacks"]),
]


def display_name(raw: str) -> str:
    """'Jackfruit/Kathal (dry)' -> 'Jackfruit (dry)'; vernacular aliases in capitalised brackets are dropped."""
    name = re.sub(r"\(\(.*\)\)", "", raw)
    name = re.sub(r"\((?=[A-Z])[^)]*\)", "", name)
    name = re.sub(r"/[^\s()]+", "", name)
    return re.sub(r"\s+", " ", name).strip() or raw.strip()


def classify_diet(label: str | None, name: str, allergens: list[str], ingredients: str) -> tuple[str, str]:
    """Catalog label, raised (never lowered) when the name or ingredients show meat or egg."""
    text = re.sub(r"\beggless\b", "", f"{name} {ingredients}".lower())
    seen = "non_veg" if MEAT.search(text) else "egg" if "egg" in allergens or EGG.search(text) else "veg"
    base = LABELS.get(label or "")
    return (seen if base is None or RANK[seen] > RANK[base] else base), ("labelled" if base else "inferred")


def meal_periods_for(name: str) -> list[str]:
    for pattern, periods in PERIOD_RULES:
        if re.search(rf"\b(?:{pattern})\b", name.lower()):
            return periods
    return ["lunch", "dinner"]


def estimate_price(kcal: float, diet: str) -> float:
    """Placeholder until a manager sets the real price (the catalog carries none)."""
    return float(min(400, max(30, 5 * round((30 + 0.12 * kcal + {"veg": 0, "egg": 10, "non_veg": 40}[diet]) / 5))))


def portion_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Payload whose `unit_serving_*` values describe ONE realistic portion, or None when the catalog has no energy data.

    Implausible servings (whole-recipe quantities) are rescaled to 250 g of the per-100 g values; records that only
    have per-100 g values use the same 250 g portion.
    """
    unit_kcal = float(payload.get("unit_serving_energy_kcal") or 0)
    per_100g = float(payload.get("energy_kcal") or 0)
    if 0 < unit_kcal <= MAX_PORTION_KCAL:
        return payload
    if per_100g <= 0:
        return None
    grams = FALLBACK_PORTION_G / 100
    if unit_kcal > MAX_PORTION_KCAL:
        factor = per_100g * grams / unit_kcal
        return {**payload, **{k: float(payload.get(k) or 0) * factor for k in SERVING_KEYS}}
    return {**payload, **{f"unit_serving_{k}": float(payload.get(k) or 0) * grams for k in NUTRIENT_KEYS}}


def to_recipe(raw: dict[str, Any]) -> dict[str, Any] | None:
    code = str(raw.get("food_code") or "").strip().upper()
    name = display_name(str(raw.get("food_name") or ""))
    payload = portion_payload(raw)
    if not code or not name or payload is None:
        return None
    serving = {k: round(float(payload.get(f"unit_serving_{k}") or 0), 1)
               for k in ("protein_g", "fibre_g", "sodium_mg", "energy_kcal")}
    allergens = [a.strip().lower() for a in str(payload.get("allergens") or "").split("|")
                 if a.strip() and a.strip().lower() != "none detected"]
    ingredients = re.sub(r"\s+", " ", str(payload.get("ingredients") or ""))
    diet, source = classify_diet(payload.get("food_preference"), name, allergens, ingredients)
    recipe = {"catalog_code": code, "name": name, "diet": diet, "diet_source": source, "declared_allergens": allergens,
              "nutrition": serving, "nutrition_tags": nutrition_tags(**serving), "serving_unit": payload.get("servings_unit"),
              "ingredient_text": ingredients.lower()[:600], "evidence_status": "confirmed", "source": "qdrant",
              "component": bool(COMPONENT.search(name.lower())), "portion_normalised": payload is not raw}
    recipe["nutrient_profile"] = build_profile(recipe, payload)
    return recipe


def fetch_catalog() -> list[dict[str, Any]]:
    client, records, offset = vectors.qdrant(), [], None
    while True:
        points, offset = client.scroll(COLLECTION, limit=256, offset=offset, with_payload=FIELDS, with_vectors=False)
        records += [p.payload for p in points]
        if offset is None:
            return records


def sync_catalog(db: Any, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create or refresh one recipe per catalog entry. Never raises: the outcome is stored in `meta`."""
    if not _lock.acquire(blocking=False):
        return status(db)
    meta: dict[str, Any] = {"attempted_at": now_utc(), "error": None, "version": CATALOG_VERSION}
    try:
        records = fetch_catalog() if records is None else records
        existing = {r["catalog_code"]: r for r in db.recipes.find({"catalog_code": {"$nin": [None, ""]}},
                                                                   {"dish_id": 1, "catalog_code": 1, "source": 1})}
        ops, skipped = [], 0
        for payload in records:
            recipe = to_recipe(payload)
            current = existing.get(recipe["catalog_code"]) if recipe else None
            if recipe is None or (current and current.get("source") != "qdrant"):
                skipped += 1
                continue
            ops.append(UpdateOne(
                {"dish_id": current["dish_id"] if current else f"DISH_{recipe['catalog_code']}"},
                {"$set": {**recipe, "synced_at": now_utc()},
                 "$setOnInsert": {"on_menu": True, "price": estimate_price(recipe["nutrition"]["energy_kcal"], recipe["diet"]),
                                  "price_source": "estimated", "meal_periods": meal_periods_for(recipe["name"]),
                                  "ingredients": [], "created_at": now_utc()}}, upsert=True))
        result = db.recipes.bulk_write(ops, ordered=False) if ops else None
        meta |= {"synced_at": now_utc(), "catalog_size": len(records), "created": result.upserted_count if result else 0,
                 "refreshed": result.modified_count if result else 0, "skipped": skipped}
    except Exception as error:  # Qdrant/Mongo outages must never crash the app; the next trigger retries.
        logger.warning("Catalog sync failed: %s", error)
        meta["error"] = f"{type(error).__name__}: {str(error)[:150]}"
    finally:
        _lock.release()
    db.meta.update_one({"_id": "catalog_sync"}, {"$set": meta}, upsert=True)
    if not meta["error"]:
        enrich_in_background(db)
    return status(db)


def status(db: Any) -> dict[str, Any]:
    meta = db.meta.find_one({"_id": "catalog_sync"}, {"_id": 0}) or {}
    return {**{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in meta.items()},
            "running": _lock.locked(), "recipes": db.recipes.count_documents({}),
            "on_menu": db.recipes.count_documents({"on_menu": {"$ne": False}}),
            "images": db.recipes.count_documents({"image_url": {"$exists": True}})}


def is_due(db: Any) -> bool:
    meta = db.meta.find_one({"_id": "catalog_sync"}) or {}

    def age(key: str) -> float:
        return (now_utc() - meta[key]).total_seconds() if meta.get(key) else float("inf")
    if meta.get("error") or meta.get("version") != CATALOG_VERSION or not db.recipes.count_documents({"source": "qdrant"}, limit=1):
        return age("attempted_at") > RETRY_SECONDS
    return age("synced_at") > timedelta(hours=settings.catalog_refresh_hours).total_seconds()


def ensure_catalog(db: Any) -> None:
    """Start a background sync when the catalog is missing or stale; a fresh database fills itself."""
    if not _lock.locked() and is_due(db):
        threading.Thread(target=sync_catalog, args=(db,), daemon=True, name="catalog-sync").start()
