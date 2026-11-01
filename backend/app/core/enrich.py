"""Recipe enrichment stored on the recipe document (master data, not recommendations):
macro + micronutrient profile from the INDB-based Qdrant `food_nutrients` collection, and an open-licence
dish photo from Wikimedia Commons via the Wikipedia API."""

import logging
import os
import ssl
import threading
from typing import Any

import httpx

from .common import now_utc

logger = logging.getLogger(__name__)
_lock = threading.Lock()

MACROS = {"energy_kcal": ("Energy", "kcal"), "protein_g": ("Protein", "g"), "carb_g": ("Carbohydrate", "g"),
          "fat_g": ("Fat", "g"), "fibre_g": ("Fibre", "g"), "freesugar_g": ("Free sugar", "g"),
          "sodium_mg": ("Sodium", "mg"), "cholesterol_mg": ("Cholesterol", "mg")}
MICROS = {"iron_mg": ("Iron", "mg"), "calcium_mg": ("Calcium", "mg"), "potassium_mg": ("Potassium", "mg"),
          "magnesium_mg": ("Magnesium", "mg"), "zinc_mg": ("Zinc", "mg"), "phosphorus_mg": ("Phosphorus", "mg"),
          "vita_ug": ("Vitamin A", "µg"), "vitb1_mg": ("Vitamin B1", "mg"), "vitb2_mg": ("Vitamin B2", "mg"),
          "vitb3_mg": ("Vitamin B3", "mg"), "vitb6_mg": ("Vitamin B6", "mg"), "folate_ug": ("Folate", "µg"),
          "vitc_mg": ("Vitamin C", "mg"), "vitd_ug": ("Vitamin D", "µg"), "vite_mg": ("Vitamin E", "mg"),
          "vitk1_ug": ("Vitamin K1", "µg")}
# Approximate adult daily reference values, used only to show "% of a day".
DAILY_REFERENCE = {"energy_kcal": 2000, "protein_g": 54, "carb_g": 275, "fat_g": 67, "fibre_g": 30, "freesugar_g": 25,
                   "sodium_mg": 2000, "cholesterol_mg": 300, "iron_mg": 19, "calcium_mg": 1000, "potassium_mg": 3500,
                   "magnesium_mg": 440, "zinc_mg": 17, "phosphorus_mg": 1000, "vita_ug": 1000, "vitb1_mg": 1.4,
                   "vitb2_mg": 2.0, "vitb3_mg": 14, "vitb6_mg": 1.9, "folate_ug": 300, "vitc_mg": 80, "vitd_ug": 15,
                   "vite_mg": 15, "vitk1_ug": 55}
WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ECOS-cafeteria-prototype/1.0 (internal demo; ecos-demo@example.com) httpx"
PROFILE_VERSION = 2


def _serving_values(payload: dict[str, Any]) -> dict[str, float]:
    def value(key: str) -> float:
        return float(payload.get(f"unit_serving_{key}") or 0)
    values = {k: value(k) for k in {**MACROS, **MICROS} if k != "vitd_ug"}
    values["vitd_ug"] = value("vitd2_ug") + value("vitd3_ug")
    return values


def build_profile(recipe: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Per cafeteria portion: INDB unit-serving values scaled so energy matches the recipe's portion.

    Values the recipe declares itself (protein, fibre, sodium, energy) take precedence, so tags and cards agree.
    """
    values = _serving_values(payload)
    declared = {k: float(v) for k, v in recipe.get("nutrition", {}).items() if v}
    portion_kcal = declared.get("energy_kcal", 0)
    scale = portion_kcal / values["energy_kcal"] if portion_kcal and values["energy_kcal"] else 1.0
    values = {k: declared.get(k, v * scale) for k, v in values.items()}

    def rows(spec: dict[str, tuple[str, str]]) -> list[dict[str, Any]]:
        return [{"key": k, "label": label, "unit": unit, "amount": round(values[k], 2),
                 "daily_pct": round(100 * values[k] / DAILY_REFERENCE[k], 1)} for k, (label, unit) in spec.items()]
    return {"source": f"INDB {payload.get('food_code')} · {payload.get('alias_name') or payload.get('food_name')}",
            "basis": "per cafeteria portion", "serving_unit": payload.get("servings_unit"), "version": PROFILE_VERSION,
            "macros": rows(MACROS), "micros": rows(MICROS), "updated_at": now_utc()}


def _qdrant_payloads(codes: list[str]) -> dict[str, dict[str, Any]]:
    from qdrant_client.http import models

    from .semantic import COLLECTION, _resources

    client, _ = _resources()
    points, _ = client.scroll(COLLECTION, limit=len(codes) + 5, with_vectors=False, scroll_filter=models.Filter(
        must=[models.FieldCondition(key="food_code", match=models.MatchAny(any=codes))]))
    return {p.payload["food_code"]: p.payload for p in points}


def _http() -> httpx.Client:
    try:
        import truststore  # Uses the OS trust store, so corporate TLS inspection certificates are honoured.
        verify: Any = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        verify = True
    return httpx.Client(verify=verify, timeout=8, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def find_image(client: httpx.Client, term: str) -> dict[str, str]:
    """Lead image of the best-matching Wikipedia article (Wikimedia Commons, open licences)."""
    base = {"action": "query", "prop": "pageimages|info", "piprop": "thumbnail", "pithumbsize": 640,
            "inprop": "url", "format": "json", "redirects": 1}
    for params in ({"titles": term}, {"generator": "search", "gsrsearch": f"{term} dish", "gsrlimit": 1}):
        pages = client.get(WIKI_API, params={**base, **params}).json().get("query", {}).get("pages", {})
        page = next((p for p in pages.values() if p.get("thumbnail")), None)
        if page:
            return {"image_url": page["thumbnail"]["source"].split("?")[0], "image_credit": page.get("fullurl", "")}
    return {"image_url": "", "image_credit": ""}


def enrich_recipes(db: Any) -> int:
    """Fill missing nutrient profiles and images; safe to call repeatedly (only missing fields are fetched)."""
    if os.getenv("ECOS_ENRICH", "true").lower() != "true" or not _lock.acquire(blocking=False):
        return 0
    updated = 0
    try:
        stale = {"nutrient_profile.version": {"$ne": PROFILE_VERSION}, "catalog_code": {"$nin": [None, ""]}}
        recipes = list(db.recipes.find({"$or": [stale, {"image_url": {"$exists": False}}]}))
        needs_profile = [r for r in recipes if r.get("catalog_code") and
                         (r.get("nutrient_profile") or {}).get("version") != PROFILE_VERSION]
        codes = [r["catalog_code"] for r in needs_profile]
        try:
            payloads = _qdrant_payloads(codes) if codes else {}
        except Exception as error:  # Qdrant optional; retried on next startup.
            logger.warning("Nutrient enrichment unavailable: %s", error)
            payloads = {}
        with _http() as client:
            for recipe in recipes:
                changes: dict[str, Any] = {}
                payload = payloads.get(recipe.get("catalog_code"))
                if payload and recipe in needs_profile:
                    changes["nutrient_profile"] = build_profile(recipe, payload)
                if "image_url" not in recipe:
                    term = recipe.get("image_query") or (payload or {}).get("alias_name") or recipe["name"]
                    try:
                        changes.update(find_image(client, term))
                    except (httpx.HTTPError, ValueError) as error:
                        logger.warning("Image lookup failed for %s: %s", recipe["dish_id"], error)
                if changes:
                    db.recipes.update_one({"dish_id": recipe["dish_id"]}, {"$set": changes})
                    updated += 1
    finally:
        _lock.release()
    return updated


def enrich_in_background(db: Any) -> None:
    threading.Thread(target=enrich_recipes, args=(db,), daemon=True, name="recipe-enrichment").start()
