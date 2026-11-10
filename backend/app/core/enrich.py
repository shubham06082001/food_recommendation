"""Recipe enrichment stored on the recipe document (master data, not recommendations):
nutrient profiles for legacy recipes, and open-licence dish photos from Wikimedia Commons.

Photos are only accepted when the file title names the same dish (every word of the dish name) and does not
mention a contradicting ingredient (e.g. mutton for a vegetable dish). No verified match means no photo.
"""

import logging
import os
import re
import ssl
import threading
import time
from typing import Any

import httpx
from qdrant_client.http import models

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
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ECOS-cafeteria/1.0 (internal cafeteria app; ecos-demo@example.com) httpx"
PROFILE_VERSION = 2
IMAGE_VERSION = 4  # Bump to re-verify every photo with newer matching rules.
IMAGE_WIDTH = 330  # A standard Wikimedia thumbnail size: small, and usually pre-rendered so it loads fast.
REQUEST_PAUSE = 0.25
FALLBACK_SEARCH = {"veg": "Indian vegetarian food", "egg": "Indian egg dish", "non_veg": "Indian meat dish"}
_fallback_images: dict[str, dict[str, Any]] = {}
_fallback_attempted: set[str] = set()

FILLER = {"with", "and", "the", "for", "dry", "wet", "curry", "style", "plain"}
SYNONYMS = {"veg": "vegetable", "veggie": "vegetable", "omlet": "omelette", "omelet": "omelette",
            "biriyani": "biryani", "parantha": "paratha", "khichri": "khichdi", "daliya": "dalia",
            "pakoda": "pakora", "cheela": "chilla", "laddoo": "ladoo", "chowmein": "chow"}


def _stem(word: str) -> str:
    word = SYNONYMS.get(word, word)
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _tokens(text: str, brackets: bool = False) -> set[str]:
    """Significant words; bracketed text is ignored in dish names (aliases) but kept in file titles."""
    text = text.lower() if brackets else re.sub(r"\([^)]*\)", " ", text.lower())
    return {_stem(w) for w in re.findall(r"[a-z]+", text) if len(w) > 2 and w not in FILLER}


MEAT = {_stem(w) for w in ("chicken mutton lamb beef pork bacon ham fish prawn shrimp crab lobster keema meat sausage "
                           "salami turkey veal tuna salmon squid duck goat hamburger").split()}
EGG = {"egg", "omelette"}
PHOTO_NOISE = {"img", "image", "photo", "picture", "pic", "jpg", "home", "made", "homemade", "closeup", "close", "view",
               "served", "plate", "bowl", "dsc", "front", "side", "fresh", "traditional"}
EXTRA_WORDS = 3  # A longer title usually shows several dishes on one plate, which would not be factual for one dish.
FILE_EXTENSION = re.compile(r"\.[a-z0-9]+$")


def _title_tokens(title: str) -> set[str]:
    title = FILE_EXTENSION.sub("", title.lower().removeprefix("file:"))
    return _tokens(title, brackets=True)


def _forbidden_ingredients(diet: str) -> set[str]:
    if diet == "veg":
        return MEAT | EGG
    return MEAT if diet == "egg" else set()


def image_matches(title: str, name: str, diet: str) -> bool:
    """True only if the Commons file title names the dish and does not contradict its diet."""
    wanted = _tokens(name)
    found = _title_tokens(title) - PHOTO_NOISE
    return (bool(wanted) and wanted <= found and len(found) <= len(wanted) + EXTRA_WORDS
            and not found & _forbidden_ingredients(diet))


def _diet_safe(title: str, diet: str) -> bool:
    return not _title_tokens(title) & _forbidden_ingredients(diet)


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


def _http() -> httpx.Client:
    try:
        import truststore  # pylint: disable=import-outside-toplevel
        verify: Any = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # Honours corporate TLS-inspection certificates.
    except ImportError:
        verify = True
    return httpx.Client(verify=verify, timeout=8, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def _search_images(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    params = {"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": query, "gsrlimit": 30,
              "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": IMAGE_WIDTH, "format": "json"}
    pages = client.get(COMMONS_API, params=params).json().get("query", {}).get("pages", {})
    return sorted(pages.values(), key=lambda page: page.get("index", 99))


def _image_details(page: dict[str, Any], representative: bool = False) -> dict[str, Any] | None:
    info = (page.get("imageinfo") or [{}])[0]
    if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        return None
    url = info.get("thumburl") or info.get("url", "")
    if not url:
        return None
    return {"image_url": url, "image_credit": info.get("descriptionurl", ""),
            "image_is_fallback": representative}


def _representative_image(client: httpx.Client, diet: str) -> dict[str, Any] | None:
    if diet not in _fallback_attempted:
        for page in _search_images(client, FALLBACK_SEARCH.get(diet, FALLBACK_SEARCH["veg"])):
            if _diet_safe(page.get("title", ""), diet) and (result := _image_details(page, True)):
                _fallback_images[diet] = result
                break
        _fallback_attempted.add(diet)
    return _fallback_images.get(diet)


def find_image(client: httpx.Client, name: str, diet: str) -> dict[str, Any] | None:
    """Find a recipe photo, then reuse a diet-safe representative photo if no exact match exists."""
    pages = _search_images(client, name)
    for page in pages:
        if image_matches(page["title"], name, diet) and (result := _image_details(page)):
            return result
    wanted = _tokens(name)
    candidates = []
    for page in pages:
        title = page.get("title", "")
        found = _title_tokens(title) - PHOTO_NOISE
        overlap = len(wanted & found)
        minimum = 1 if len(wanted) == 1 else 2
        if overlap >= minimum and _diet_safe(title, diet):
            candidates.append((overlap / len(wanted), page))
    for _, page in sorted(candidates, key=lambda match: match[0], reverse=True):
        if result := _image_details(page):
            return result
    return _representative_image(client, diet)


def _fill_profiles(db: Any) -> int:
    """Legacy/manager recipes linked to the catalog by code get a nutrient profile from Qdrant."""
    from . import vectors  # pylint: disable=import-outside-toplevel
    from .semantic import COLLECTION  # pylint: disable=import-outside-toplevel

    recipes = list(db.recipes.find({"catalog_code": {"$nin": [None, ""]}, "nutrient_profile.version": {"$ne": PROFILE_VERSION}}))
    if not recipes:
        return 0
    try:
        points, _ = vectors.qdrant().scroll(COLLECTION, limit=len(recipes) + 5, with_vectors=False,
                                            scroll_filter=models.Filter(must=[models.FieldCondition(
                                                key="food_code", match=models.MatchAny(any=[r["catalog_code"] for r in recipes]))]))
    except Exception as error:  # Qdrant is optional; retried on the next run.
        logger.warning("Nutrient enrichment unavailable: %s", error)
        return 0
    payloads = {p.payload["food_code"]: p.payload for p in points}
    updated = 0
    for recipe in recipes:
        if payload := payloads.get(recipe["catalog_code"]):
            db.recipes.update_one({"dish_id": recipe["dish_id"]}, {"$set": {"nutrient_profile": build_profile(recipe, payload)}})
            updated += 1
    return updated


def _fill_images(db: Any) -> int:
    todo = list(db.recipes.find({"image_version": {"$ne": IMAGE_VERSION}, "image_source": {"$ne": "manager"}},
                                {"dish_id": 1, "name": 1, "diet": 1}).sort("on_menu", -1))
    found_count, failures = 0, 0
    with _http() as client:
        for recipe in todo:
            try:
                found = find_image(client, recipe["name"], recipe.get("diet", "veg"))
            except (httpx.HTTPError, ValueError) as error:
                failures += 1
                logger.warning("Image lookup failed for %s: %s", recipe["dish_id"], error)
                if failures >= 5:  # Offline or blocked: stop and retry on the next run.
                    break
                continue
            change = ({"$set": {**found, "image_version": IMAGE_VERSION}} if found else
                      {"$set": {"image_version": IMAGE_VERSION},
                       "$unset": {"image_url": "", "image_credit": "", "image_is_fallback": ""}})
            db.recipes.update_one({"dish_id": recipe["dish_id"]}, change)
            found_count += bool(found)
            time.sleep(REQUEST_PAUSE)
    return found_count


def enrich_recipes(db: Any) -> int:
    """Fill missing nutrient profiles and verified images; safe to call repeatedly."""
    if os.getenv("ECOS_ENRICH", "true").lower() != "true" or not _lock.acquire(blocking=False):
        return 0
    try:
        return _fill_profiles(db) + _fill_images(db)
    finally:
        _lock.release()


def enrich_in_background(db: Any) -> None:
    threading.Thread(target=enrich_recipes, args=(db,), daemon=True, name="recipe-enrichment").start()
