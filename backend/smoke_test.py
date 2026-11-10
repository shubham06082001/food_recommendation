"""End-to-end smoke test of the ECOS API against a throwaway database (ECOS_test).

Run: ECOS_MONGODB_DB=ECOS_test .venv/bin/python -m backend.smoke_test

Starts from a completely empty database (the "switch to a new DB" case), then bootstraps, syncs a fake Qdrant
catalog, and exercises auth, menu curation, recommendations, ordering, inventory, forecasting and dashboards.
"""

import io
import os
import sys
import tempfile
from collections import Counter
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

assert os.getenv("ECOS_MONGODB_DB", "").endswith("_test"), "Set ECOS_MONGODB_DB=ECOS_test to protect real data"
# Train into a throwaway folder so test runs never overwrite real model artifacts; keep tests offline.
os.environ.setdefault("ECOS_ML_ARTIFACTS", tempfile.mkdtemp(prefix="ecos_ml_"))
os.environ.setdefault("ECOS_ENRICH", "false")
os.environ.setdefault("ECOS_MANAGER_PASSWORD", "Manager-Test-1")

from fastapi.testclient import TestClient  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from backend.app.core import catalog, enrich, menu, recommender, vectors  # noqa: E402
from backend.app.core.common import eligibility  # noqa: E402
from backend.app.core.config import settings  # noqa: E402
from backend.app.core.database import ensure_indexes, get_db  # noqa: E402
from backend.app.core.security import hash_password, verify_password  # noqa: E402
from backend.app.core.seed import bootstrap, seed_demo, seed_demo_history  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.routers import copilot  # noqa: E402

failures: list[str] = []
vectors.cool_down(10**6)  # No Qdrant/model in tests: ranking falls back to goal rules.
MANAGER, MANAGER_PASSWORD, EMPLOYEE_PASSWORD = settings.manager_id, settings.manager_password, "Employee-Pass-1"
TOKENS: dict[str, str] = {}


def check(label: str, condition: bool, detail: object = "") -> None:
    print(("PASS " if condition else "FAIL ") + label + ("" if condition else f" -> {detail}"))
    if not condition:
        failures.append(label)


def payload(code: str, name: str, label: str | None, allergens: str, ingredients: str | None, kcal: float = 250.0,
            protein: float = 8.0, fibre: float = 3.0, unit_kcal: float | None = None) -> dict:
    """A catalog record shaped like a Qdrant `food_nutrients` payload."""
    return {"food_code": code, "food_name": name, "food_preference": label, "allergens": allergens,
            "ingredients": ingredients, "servings_unit": "bowl", "energy_kcal": kcal / 2.5,
            "unit_serving_energy_kcal": kcal if unit_kcal is None else unit_kcal, "unit_serving_protein_g": protein,
            "unit_serving_fibre_g": fibre, "unit_serving_sodium_mg": 200.0}


CATALOG = [
    payload("CAT001", "Paneer soup", None, "Milk", None, kcal=292, protein=19.7),
    payload("CAT002", "Chicken soup", "non_veg", "none detected", "chicken | water"),
    payload("CAT003", "Wheat porridge (Gehun daliya)", "veg", "Wheat", "wheat | milk"),
    payload("CAT004", "Cabbage rolls (dry) ((Pattagobhi rolls) (dry))", "egg", "Egg", "1 lb. hamburger | 1 egg"),
    payload("CAT005", "Whole recipe pot", "veg", "none detected", None, kcal=140 * 2.5, unit_kcal=4876),
    payload("CAT006", "Idli", "veg", "none detected", "rice | urad dal", kcal=210, protein=6),
    payload("ASC123", "Vegetable biryani/biriyani", "veg", "Milk", None, kcal=527),  # Manager-authored twin.
    {"food_code": "CAT008", "food_name": "No nutrition data"},
]


def pure_checks() -> None:
    check("display name drops vernacular aliases", catalog.display_name("Cabbage rolls (dry) ((Pattagobhi rolls) (dry))")
          == "Cabbage rolls (dry)" and catalog.display_name("Jackfruit/Kathal (Kathal ki sabzi)") == "Jackfruit")
    check("diet is raised by ingredients, never lowered", catalog.classify_diet("egg", "Rolls", [], "1 lb hamburger")[0] == "non_veg"
          and catalog.classify_diet(None, "Eggplant curry", [], "")[0] == "veg"
          and catalog.classify_diet(None, "Eggless cake", [], "")[0] == "veg"
          and catalog.classify_diet("jain_food", "Dal", [], "")[0] == "veg")
    check("meal periods inferred", catalog.meal_periods_for("Idli") == ["breakfast"]
          and catalog.meal_periods_for("Paneer butter masala") == ["lunch", "dinner"]
          and "snacks" in catalog.meal_periods_for("Veg sandwich"))
    check("price estimate bounded", 30 <= catalog.estimate_price(1, "veg") and catalog.estimate_price(5000, "non_veg") == 400)
    check("components are flagged, dishes are not", all(catalog.COMPONENT.search(n) for n in ("mixed stock", "short crust pastry dough", "gravy for kofta"))
          and not any(catalog.COMPONENT.search(n) for n in ("paneer butter masala", "vegetable biryani", "tomato soup")))
    check("image must name the dish and not contradict its diet",
          not enrich.image_matches("File:Mutton biryani.jpg", "Vegetable biryani", "veg")
          and enrich.image_matches("File:Vegetable Biryani IMG 001.jpg", "Vegetable biryani", "veg")
          and not enrich.image_matches("File:Veg biryani (chicken).jpg", "Vegetable biryani", "veg")
          and not enrich.image_matches("File:Biryani.jpg", "Vegetable biryani", "veg")
          and not enrich.image_matches("File:Paneer curry with lamb mince and samosas and rice.jpg", "Paneer curry", "veg")
          and enrich.image_matches("File:Mutton biryani.jpg", "Mutton biryani", "non_veg")
          and not enrich._diet_safe("File:Chicken curry.jpg", "veg")
          and not enrich._diet_safe("File:Egg curry.jpg", "veg")
          and enrich._diet_safe("File:Paneer curry.jpg", "veg"))
    check("password hashing", verify_password("S3cret-pass", hash_password("S3cret-pass"))
          and not verify_password("wrong", hash_password("S3cret-pass")) and not verify_password("x", "garbage"))
    check("allergen aliases are symmetrical",
          not eligibility({"diet": "veg", "declared_allergens": ["wheat"]}, {"declared_allergens": ["gluten"]})[0]
          and not eligibility({"diet": "veg", "declared_allergens": ["gluten"]}, {"declared_allergens": ["wheat"]})[0]
          and not eligibility({"diet": "veg", "declared_allergens": ["milk"]}, {"declared_allergens": ["dairy"]})[0]
          and eligibility({"diet": "veg", "declared_allergens": ["soy"]}, {"declared_allergens": ["milk"]})[0])
    stock = {"I": {"quantity": 100, "unit": "g"}, "K": {"quantity": 1, "unit": "kg"}}
    check("stock maths: repeated lines summed, units converted, untracked always available",
          menu.max_portions({"ingredients": [{"ingredient_id": "I", "quantity": 10}] * 2}, stock) == 5
          and menu.max_portions({"ingredients": [{"ingredient_id": "K", "quantity": 100, "unit": "g"}]}, stock) == 10
          and menu.max_portions({"ingredients": [{"ingredient_id": "I", "quantity": 1, "unit": "ml"}]}, stock) == 0
          and menu.max_portions({}, stock) == menu.UNTRACKED_PORTIONS)
    intent = recommender.parse_query("light dinner without milk and peanuts under 150")
    check("query: several exclusions parsed", intent["excluded_allergens"] == ["milk", "peanut"] and intent["max_price"] == 150, intent)

    def item(dish_id: str, name: str, code: str) -> dict:
        return {"dish_id": dish_id, "name": name, "catalog_code": code, "price": 100, "diet": "veg", "meal_period": "lunch",
                "ingredients": [], "available": True, "maximum_portions": 20, "nutrition": {}, "nutrition_tags": []}
    fake = MagicMock()
    with patch.object(recommender, "menu_items", return_value=[item("D_PANEER", "Paneer bowl", "C1"),
                                                               item("D_CHEESE", "Cottage cheese bowl", "C2")]), \
            patch.object(recommender, "_history", return_value=(Counter(), {}, {}, Counter())), \
            patch.object(recommender, "semantic_scores", return_value={"C1": 0.1, "C2": 0.99}):
        rec = recommender.recommend(fake, {"user_id": "U"}, "paneer", "lunch", 6, [])
    check("strong semantic match survives alongside a literal match", {i["dish_id"] for i in rec["items"]} == {"D_PANEER", "D_CHEESE"}, rec["items"])


pure_checks()

with patch("backend.app.main.ensure_catalog"), patch("backend.app.routers.menus.ensure_catalog") as auto_sync, \
        patch.object(copilot, "_llm", return_value=None), TestClient(app) as client:
    db = get_db()
    for name in db.list_collection_names():  # A brand-new database: nothing exists yet.
        db[name].drop()
    ensure_indexes(db)
    bootstrap(db)

    def h(user_id: str) -> dict:
        if user_id not in TOKENS:
            password = MANAGER_PASSWORD if user_id == MANAGER else EMPLOYEE_PASSWORD
            r = client.post("/api/v1/auth/login", json={"user_id": user_id, "password": password})
            TOKENS[user_id] = r.json()["session_token"]
        return {"X-Session-Token": TOKENS[user_id]}

    check("health on an empty database", client.get("/api/v1/health").status_code == 200)

    # Authentication
    r = client.post("/api/v1/auth/login", json={"user_id": MANAGER, "password": MANAGER_PASSWORD})
    check("manager logs in with the configured password", r.status_code == 200 and r.json()["role"] == "manager", r.text)
    settings.manager_password = "A-different-password-9"
    bootstrap(db)  # A changed .env password is applied on the next start.
    check("manager password follows .env", client.post("/api/v1/auth/login", json={
        "user_id": MANAGER, "password": "A-different-password-9"}).status_code == 200 and client.post(
        "/api/v1/auth/login", json={"user_id": MANAGER, "password": MANAGER_PASSWORD}).status_code == 401)
    settings.manager_password = MANAGER_PASSWORD
    bootstrap(db)
    check("manager wrong password rejected", client.post("/api/v1/auth/login", json={"user_id": MANAGER,
                                                         "password": "not-the-password"}).status_code == 401)
    check("manager cannot be claimed or created by login", client.post("/api/v1/auth/login", json={
        "user_id": "mgr777", "password": "Employee-Pass-1"}).json()["role"] == "employee")
    check("login needs a password", client.post("/api/v1/auth/login", json={"user_id": "EMP001"}).status_code == 422
          and client.post("/api/v1/auth/login", json={"user_id": "EMP001", "password": "short"}).status_code == 422)
    r = client.post("/api/v1/auth/login", json={"user_id": "emp001", "password": EMPLOYEE_PASSWORD})
    check("new employee registers on first login", r.status_code == 200 and r.json()["user_id"] == "EMP001"
          and r.json()["role"] == "employee" and not r.json()["profile_complete"], r.text)
    check("employee wrong password rejected", client.post("/api/v1/auth/login", json={
        "user_id": "EMP001", "password": "Wrong-Pass-123"}).status_code == 401)
    user_doc = db.users.find_one({"user_id": "EMP001"})
    check("password stored hashed", user_doc["password_hash"].startswith("scrypt$") and EMPLOYEE_PASSWORD not in str(user_doc))
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"user_id": "EMP001", "password": "Wrong-Pass-123"})
    check("account locks after repeated failures", client.post("/api/v1/auth/login", json={
        "user_id": "EMP001", "password": EMPLOYEE_PASSWORD}).status_code == 429)
    db.users.update_one({"user_id": "EMP001"}, {"$unset": {"locked_until": ""}, "$set": {"failed_logins": 0}})

    login = client.post("/api/v1/auth/login", json={"user_id": "EMP001", "password": EMPLOYEE_PASSWORD}).json()
    token = login.get("session_token", "")
    check("login issues session token", len(token) > 30 and login["session_minutes"] == 30, login)
    check("session token stored only as a hash", db.sessions.count_documents({"token": token}) == 0
          and db.sessions.count_documents({"token_hash": {"$exists": True}}) >= 1)
    check("a bare user id no longer authenticates", client.get("/api/v1/users/EMP001", headers={"X-User-Id": "EMP001"}).status_code == 401
          and client.post("/api/v1/recipes/bulk-menu", json={"on_menu": True}, headers={"X-User-Id": MANAGER}).status_code == 401)
    first = db.sessions.find_one({"user_id": "EMP001"})["expires_at"]
    r = client.get("/api/v1/auth/session", headers={"X-Session-Token": token})
    check("session restores user", r.status_code == 200 and r.json()["user_id"] == "EMP001", r.text)
    check("session expiry slides", db.sessions.find_one({"user_id": "EMP001"})["expires_at"] >= first)
    check("unknown session rejected", client.get("/api/v1/auth/session", headers={"X-Session-Token": "x" * 40}).status_code == 401)
    client.post("/api/v1/auth/logout", headers={"X-Session-Token": token})
    check("logout revokes session", client.get("/api/v1/auth/session", headers={"X-Session-Token": token}).status_code == 401
          and client.get("/api/v1/users/EMP001", headers={"X-Session-Token": token}).status_code == 401)

    # A new, empty database must not crash anything
    r = client.get("/api/v1/menu", params={"meal_period": "lunch"}, headers=h("EMP001"))
    check("empty database: menu is empty, not an error, and a catalog sync is requested",
          r.status_code == 200 and r.json()["items"] == [] and r.json()["catalog_empty"] and auto_sync.called, r.text[:200])
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch"}, headers=h("EMP001"))
    check("empty database: recommendations are empty, not an error", r.status_code == 200 and r.json()["items"] == [], r.text[:200])
    check("empty database: manager lists", client.get("/api/v1/recipes", headers=h(MANAGER)).json()["total"] == 0
          and client.get("/api/v1/catalog/status", headers=h(MANAGER)).status_code == 200)
    check("empty database: dashboards", client.get("/api/v1/dashboard/manager", headers=h(MANAGER)).status_code == 200
          and client.get("/api/v1/dashboard/employee/EMP001", headers=h("EMP001")).status_code == 200)

    # Catalog sync from (fake) Qdrant, on top of the optional demo data
    seed_demo(db)
    demo_recipes = db.recipes.count_documents({})
    result = catalog.sync_catalog(db, records=CATALOG)
    check("catalog sync creates one recipe per usable record", result["created"] == 6 and result["skipped"] == 2
          and result["recipes"] == demo_recipes + 6 and not result.get("error"), result)
    check("manager-authored recipe is not overwritten or duplicated", db.recipes.find_one({"dish_id": "DISH_VEG_BIRYANI"})["name"]
          == "Vegetable biryani" and db.recipes.count_documents({"catalog_code": "ASC123"}) == 1)
    cabbage = db.recipes.find_one({"dish_id": "DISH_CAT004"})
    check("catalog mapping: name, diet raised by ingredients", cabbage["name"] == "Cabbage rolls (dry)" and cabbage["diet"] == "non_veg", cabbage)
    pot = db.recipes.find_one({"dish_id": "DISH_CAT005"})
    check("implausible catalog serving is normalised to one portion", pot["portion_normalised"] and pot["nutrition"]["energy_kcal"] <= 900
          and pot["nutrient_profile"]["macros"][0]["amount"] <= 900, pot["nutrition"])
    check("new recipes default onto the menu with an estimated price", all(
        r["on_menu"] and r["price_source"] == "estimated" and r["price"] > 0 for r in db.recipes.find({"source": "qdrant"})))
    check("empty/stale detection", not catalog.is_due(db))

    # Menu: paged, searchable, personalised
    r = client.get("/api/v1/menu", params={"meal_period": "lunch", "limit": 5}, headers=h("EMP001"))
    lunch = r.json()
    check("menu is paged", r.status_code == 200 and len(lunch["items"]) == 5 and lunch["total"] > 5 and not lunch["catalog_empty"], r.text[:200])
    r2 = client.get("/api/v1/menu", params={"meal_period": "lunch", "limit": 5, "offset": 5}, headers=h("EMP001"))
    check("menu pages do not overlap", not {i["dish_id"] for i in lunch["items"]} & {i["dish_id"] for i in r2.json()["items"]})
    client.put("/api/v1/users/EMP001/preferences", headers=h("EMP001"), json={
        "name": "Riya", "dietary_preference": "vegetarian", "wellness_goals": ["high_protein", "high_fibre"],
        "declared_allergens": ["Peanut"], "favourite_categories": ["indian"], "consented": True})
    r = client.get("/api/v1/menu", params={"q": "chicken"}, headers=h("EMP001"))
    check("menu search + non-veg flagged ineligible for vegetarian", r.json()["total"] == 1 and r.json()["items"][0]["eligible"] is False, r.text[:300])
    check("menu requires login", client.get("/api/v1/menu").status_code == 401)

    # Manager curation: add / remove recipes from the menu
    check("employee cannot curate", client.patch("/api/v1/recipes", json={"updates": [{"dish_id": "DISH_CAT001", "on_menu": False}]},
                                                 headers=h("EMP001")).status_code == 403)
    r = client.patch("/api/v1/recipes", json={"updates": [{"dish_id": "DISH_CAT001", "on_menu": False, "price": 99}]}, headers=h(MANAGER))
    check("manager excludes a recipe and sets its price", r.status_code == 200 and r.json()["updated"] == 1, r.text)
    check("excluded recipe leaves menu and recommendations",
          client.get("/api/v1/menu", params={"q": "paneer soup"}, headers=h("EMP001")).json()["total"] == 0
          and all(i["dish_id"] != "DISH_CAT001" for i in client.post("/api/v1/recommendations", json={"limit": 20, "query": "paneer soup"},
                                                                        headers=h("EMP001")).json()["items"]))
    check("excluded recipe still visible to the manager", client.get("/api/v1/recipes", params={"on_menu": "false"}, headers=h(MANAGER)).json()["total"] == 1)
    client.post("/api/v1/catalog/sync", headers=h(MANAGER))  # Real Qdrant is skipped in tests; re-sync below uses fake records.
    catalog.sync_catalog(db, records=CATALOG)
    kept = db.recipes.find_one({"dish_id": "DISH_CAT001"})
    check("re-sync keeps manager choices", kept["on_menu"] is False and kept["price"] == 99 and kept["price_source"] == "manager", kept)
    r = client.post("/api/v1/recipes/bulk-menu", json={"on_menu": False, "q": "soup"}, headers=h(MANAGER))
    check("bulk exclude by search", r.status_code == 200 and r.json()["matched"] == 2, r.text)
    r = client.post("/api/v1/recipes/bulk-menu", json={"on_menu": True, "q": "soup"}, headers=h(MANAGER))
    check("bulk include by search", r.json()["updated"] == 2 and db.recipes.count_documents({"on_menu": False}) == 0, r.text)
    check("unknown dish rejected", client.patch("/api/v1/recipes", json={"updates": [{"dish_id": "NOPE", "on_menu": True}]},
                                                headers=h(MANAGER)).status_code == 404)
    check("meal periods are editable", client.patch("/api/v1/recipes", json={"updates": [{"dish_id": "DISH_CAT006", "meal_periods": [
        "breakfast", "lunch"]}]}, headers=h(MANAGER)).status_code == 200
          and any(i["dish_id"] == "DISH_CAT006" for i in client.get("/api/v1/menu", params={"meal_period": "lunch", "limit": 60},
                                                                    headers=h("EMP001")).json()["items"]))

    # Recommendations
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "query": "high protein vegetarian lunch", "limit": 5},
                    headers=h("EMP001"))
    rec = r.json()
    check("recommendations", r.status_code == 200 and rec["items"], r.text[:300])
    check("recommendations exclude non-veg", all(i["diet"] == "veg" for i in rec["items"]), rec["items"])
    check("top recommendation matches a goal", rec["items"][0]["goal_matches"] >= 1, rec["items"][0])
    check("recommendations are not stored", "recommendation_event_id" not in rec and db.recommendation_events.count_documents({}) == 0)
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "limit": 10, "query": "without milk under 120"}, headers=h("EMP001"))
    got = r.json()["items"]
    check("query exclusions and budget applied", got and all("milk" not in i["declared_allergens"] and i["price"] <= 120 for i in got), got)
    first_page = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "limit": 3}, headers=h("EMP001")).json()
    second_page = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "limit": 3, "offset": 3}, headers=h("EMP001")).json()
    check("offset paging gives new dishes and no 422 at depth", first_page["has_more"] and not {i["dish_id"] for i in first_page["items"]}
          & {i["dish_id"] for i in second_page["items"]} and client.post("/api/v1/recommendations", json={"limit": 3, "offset": 900},
                                                                          headers=h("EMP001")).status_code == 200)
    r = client.post("/api/v1/recommendations", json={"query": "peanut free breakfast", "limit": 5}, headers=h("EMP001"))
    check("query can set the meal period", r.json()["meal_period"] == "breakfast", r.text[:300])
    check("recommendations carry nutrients", all("nutrient_profile" in i and "image_url" in i for i in r.json()["items"]), r.text[:300])
    client.post("/api/v1/auth/login", json={"user_id": "EMP004", "password": EMPLOYEE_PASSWORD})
    client.put("/api/v1/users/EMP004/preferences", headers=h("EMP004"), json={
        "dietary_preference": "no_preference", "declared_allergens": ["gluten"], "consented": True})
    r = client.post("/api/v1/recommendations", json={"meal_period": "breakfast", "limit": 20}, headers=h("EMP004"))
    names = {i["dish_id"] for i in r.json()["items"]}
    check("gluten exclusion also removes wheat-declared dishes", "DISH_RAVA_DALIA" not in names and "DISH_MEETHA_DALIA" not in names and names, names)
    r = client.post("/api/v1/recommendations/meal-plan", json={"query": "high protein"}, headers=h("EMP001"))
    plan = r.json()
    dishes = [m["dish_id"] for m in plan.get("meals", [])]
    check("meal plan: one veg pick per period, no repeats", r.status_code == 200 and len(dishes) >= 3
          and len(set(dishes)) == len(dishes) and all(m["diet"] == "veg" for m in plan["meals"]), r.text[:300])
    check("meal plan totals", plan["totals"]["price"] == sum(m["price"] for m in plan["meals"])
          and len(plan["totals"]["micros"]) == 16, plan.get("totals"))

    # Ordering: stock, safety, idempotency, rollback
    paneer_before = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    order_body = {"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 2}], "recommended_dish_ids": ["DISH_MATAR_PANEER"],
                  "client_request_id": "req-0001-abcdef"}
    r = client.post("/api/v1/orders", json=order_body, headers=h("EMP001"))
    check("place order", r.status_code == 201 and r.json()["total"] == 280, r.text)
    order_id = r.json()["order_id"]
    check("paneer deducted 300g", paneer_before - db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == 300)
    r = client.post("/api/v1/orders", json=order_body, headers=h("EMP001"))
    check("retry with the same request id returns the same order and takes no extra stock",
          r.json()["order_id"] == order_id and paneer_before - db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == 300
          and db.orders.count_documents({"user_id": "EMP001"}) == 1, r.text)
    client.post("/api/v1/auth/login", json={"user_id": "EMP003", "password": EMPLOYEE_PASSWORD})
    client.put("/api/v1/users/EMP003/preferences", headers=h("EMP003"), json={"dietary_preference": "no_preference",
                                                                              "declared_allergens": ["dairy"], "consented": True})
    check("server refuses a dish that contains a declared allergen (even if the UI is bypassed)",
          client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 1}]}, headers=h("EMP003")).status_code == 409)
    check("per-dish quantity cap cannot be bypassed with duplicate lines",
          client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_IDLI", "quantity": 10}, {"dish_id": "DISH_IDLI", "quantity": 5}]},
                      headers=h("EMP001")).status_code == 400)
    check("non-veg refused for a vegetarian", client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_CAT002", "quantity": 1}]},
                                                          headers=h("EMP001")).status_code == 409)
    stock_before = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    with patch("backend.app.routers.orders.record_movement", side_effect=PyMongoError("boom")):
        r = client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_PALAK_PANEER", "quantity": 1}]}, headers=h("EMP001"))
    check("a failed order write gives the stock back", r.status_code == 503 and db.ingredients.find_one(
        {"ingredient_id": "ING_PANEER"})["quantity"] == stock_before and db.orders.count_documents({"user_id": "EMP001"}) == 1, r.text)
    r = client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_CAT006", "quantity": 2}]}, headers=h("EMP001"))
    check("catalog dish (no stock lines) can be ordered without touching inventory", r.status_code == 201 and db.inventory_movements.count_documents(
        {"order_id": r.json()["order_id"]}) == 0, r.text)
    r = client.get("/api/v1/dashboard/employee/EMP001", headers=h("EMP001"))
    check("wellness score +10 per healthy portion", r.json()["wellness_summary"]["wellness_score"] >= 40, r.text[:300])
    check("manager cannot order", client.post("/api/v1/orders", json=order_body, headers=h(MANAGER)).status_code == 403)
    check("unknown dish rejected", client.post("/api/v1/orders", json={"items": [{"dish_id": "NOPE", "quantity": 1}]},
                                               headers=h("EMP001")).status_code == 400)

    # Push paneer to critical, then overdraw
    client.post("/api/v1/auth/login", json={"user_id": "EMP002", "password": EMPLOYEE_PASSWORD})
    client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 4}]}, headers=h("EMP002"))
    check("inventory alerts need manager", client.get("/api/v1/inventory/alerts").status_code == 401)
    alerts = client.get("/api/v1/inventory/alerts", headers=h(MANAGER)).json()["data"]
    check("paneer critical alert", any(a["ingredient_id"] == "ING_PANEER" and a["status"] == "CRITICAL" for a in alerts), alerts)
    paneer_now = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    peas_before = db.ingredients.find_one({"ingredient_id": "ING_PEAS"})["quantity"]
    # A concurrent order can take stock after the availability check: simulate by inflating the last ingredient's need.
    real_needs = menu.per_portion_needs
    with patch("backend.app.routers.orders.per_portion_needs", side_effect=lambda d, s: {**real_needs(d, s), "ING_ONION": 1e9}):
        r = client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 1}]}, headers=h("EMP002"))
    check("overdraw rejected with 409", r.status_code == 409 and "Onion" in r.text, r.text)
    check("failed order rolled back the ingredients deducted before the shortage",
          db.ingredients.find_one({"ingredient_id": "ING_PEAS"})["quantity"] == peas_before
          and db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == paneer_now)

    # Affected dishes + movements + replenish
    r = client.get("/api/v1/inventory/ING_PANEER/affected-dishes", headers=h(MANAGER))
    check("affected dishes", {"DISH_MATAR_PANEER", "DISH_PALAK_PANEER"} <= {d["dish_id"] for d in r.json()["data"]}, r.text)
    check("employee cannot replenish", client.post("/api/v1/inventory/ING_PANEER/replenish", json={"quantity": 5000},
                                                   headers=h("EMP001")).status_code == 403)
    r = client.post("/api/v1/inventory/ING_PANEER/replenish", json={"quantity": 5000, "note": "test"}, headers=h(MANAGER))
    check("replenish -> healthy", r.status_code == 200 and r.json()["status"] == "HEALTHY", r.text)
    moves = client.get("/api/v1/inventory/ING_PANEER/movements", headers=h(MANAGER)).json()["data"]
    check("movements recorded", {m["type"] for m in moves} >= {"order_consumption", "replenishment"}, moves)
    r = client.patch("/api/v1/inventory/ING_PANEER", json={"reorder_point": 2000}, headers=h(MANAGER))
    check("edit threshold", r.status_code == 200 and r.json()["data"]["reorder_point"] == 2000, r.text)
    r = client.post("/api/v1/inventory", json={"ingredient_id": "ing_ghee", "name": "Ghee", "quantity": 500, "unit": "g",
                                               "reorder_point": 100}, headers=h(MANAGER))
    check("add ingredient", r.status_code == 201, r.text)
    peas = db.ingredients.find_one({"ingredient_id": "ING_PEAS"})["quantity"]
    r = client.patch("/api/v1/inventory/ING_PEAS", json={"quantity": 4000, "note": "count"}, headers=h(MANAGER))
    check("set stock quantity", r.status_code == 200 and r.json()["data"]["quantity"] == 4000, r.text)
    moves = client.get("/api/v1/inventory/ING_PEAS/movements", headers=h(MANAGER)).json()["data"]
    check("quantity edit logged", moves[0]["type"] == "manual_adjustment" and moves[0]["quantity"] == 4000 - peas, moves[:1])
    check("employee cannot edit stock", client.patch("/api/v1/inventory/ING_PEAS", json={"quantity": 1}, headers=h("EMP001")).status_code == 403)

    # Today's consumption per order
    check("consumption needs manager", client.get("/api/v1/inventory/consumption", headers=h("EMP001")).status_code == 403)
    r = client.get("/api/v1/inventory/consumption", headers=h(MANAGER))
    use = r.json()
    paneer_use = next((i for i in use.get("ingredients", []) if i["ingredient_id"] == "ING_PANEER"), {})
    check("consumption totals paneer per order", r.status_code == 200 and paneer_use.get("used_today") == 900
          and paneer_use.get("orders") == 2, r.text[:400])
    check("consumption shows affected dishes", any(d["dish_id"] == "DISH_MATAR_PANEER" and d["portions_lost"] > 0
                                                   for d in use["affected_dishes"]), use["affected_dishes"])
    r = client.get("/api/v1/inventory/consumption", params={"query": "dairy"}, headers=h(MANAGER))
    check("consumption focus search", r.status_code == 200 and "ING_PANEER" in {m["ingredient_id"] for m in r.json()["matched_ingredients"]})

    # Order lifecycle
    for status in ("preparing", "ready", "collected"):
        r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": status}, headers=h(MANAGER))
        check(f"status -> {status}", r.status_code == 200, r.text)
    r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"}, headers=h(MANAGER))
    check("cannot cancel collected", r.status_code == 400, r.text)
    emp2_order = client.get("/api/v1/orders", headers=h("EMP002")).json()["data"][0]["order_id"]
    paneer = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    client.patch(f"/api/v1/orders/{emp2_order}/status", json={"status": "cancelled"}, headers=h(MANAGER))
    check("cancel restores stock", db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == paneer + 600)
    client.patch(f"/api/v1/orders/{emp2_order}/status", json={"status": "cancelled"}, headers=h(MANAGER))
    check("cancelling twice never restores twice", db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == paneer + 600)
    mine = client.get("/api/v1/orders", params={"user_id": "EMP002"}, headers=h("EMP001")).json()["data"]
    check("employee only sees own orders", all(o["user_id"] == "EMP001" for o in mine), mine)
    check("employee cannot open others' order", client.get(f"/api/v1/orders/{emp2_order}", headers=h("EMP001")).status_code == 403)

    # Feedback, wellness, users
    r = client.post("/api/v1/feedback", json={"order_id": order_id, "rating": 5, "reason": "taste", "comment": "Great"}, headers=h("EMP001"))
    check("feedback", r.status_code == 200, r.text)
    check("feedback on others' order 404", client.post("/api/v1/feedback", json={"order_id": emp2_order, "rating": 3},
                                                       headers=h("EMP001")).status_code == 404)
    r = client.get("/api/v1/wellness/EMP001/monthly", headers=h("EMP001"))
    w = r.json()
    check("wellness monthly", r.status_code == 200 and w["meals_tracked"] >= 2 and w["categories"]["high_protein"]["percentage"] > 0, r.text[:400])
    check("wellness recommended tracked", w["recommendation_engagement"]["recommended_meals_ordered"] == 2, w)
    check("wellness privacy", client.get("/api/v1/wellness/EMP001/monthly", headers=h("EMP002")).status_code == 403)
    check("employee cannot read other employee", client.get("/api/v1/users/EMP001", headers=h("EMP002")).status_code == 403)
    check("user record never exposes password hash", "password_hash" not in client.get("/api/v1/users/EMP001", headers=h("EMP001")).text)
    check("user list is manager-only", client.get("/api/v1/users").status_code == 401
          and client.get("/api/v1/users", headers=h("EMP001")).status_code == 403
          and "EMP001" in {u["user_id"] for u in client.get("/api/v1/users", headers=h(MANAGER)).json()["data"]})
    check("preferences require consent", client.put("/api/v1/users/EMP001/preferences", headers=h("EMP001"), json={"consented": False}).status_code == 400)
    check("employee cannot read manager dashboard", client.get("/api/v1/dashboard/manager", headers=h("EMP001")).status_code == 403)

    # Uploads
    inv = pd.DataFrame([{"ingredient_id": "ING_TOFU", "name": "Tofu", "quantity": 3000, "unit": "g", "reorder_point": 800}])
    buf = io.BytesIO()
    inv.to_excel(buf, index=False)
    buf.seek(0)
    r = client.post("/api/v1/upload/inventory", files={"file": ("inv.xlsx", buf, "application/octet-stream")}, data={"mode": "commit"}, headers=h(MANAGER))
    check("inventory upload", r.status_code == 200 and r.json()["updated"] == 1, r.text)
    bad = pd.DataFrame([{"ingredient_id": "X", "name": "", "quantity": -1, "unit": "g", "reorder_point": 1}])
    r = client.post("/api/v1/upload/inventory", files={"file": ("bad.csv", bad.to_csv(index=False).encode(), "text/csv")},
                    data={"mode": "commit"}, headers=h(MANAGER))
    check("bad inventory upload rejected", r.status_code == 200 and not r.json()["success"] and r.json()["errors"], r.text)
    r = client.post("/api/v1/upload/inventory", files={"file": ("inf.csv", b"ingredient_id,name,quantity,unit,reorder_point\nINF,Inf,inf,g,1\n", "text/csv")},
                    data={"mode": "commit"}, headers=h(MANAGER))
    check("infinite quantity rejected", not r.json()["success"], r.text)
    rec_df = pd.DataFrame([
        {"dish_id": "DISH_TOFU_BOWL", "dish_name": "Tofu bowl", "ingredient_id": "ING_TOFU", "quantity_per_portion": 150, "price": 150,
         "diet": "veg", "meal_periods": "lunch|dinner", "allergens": "soy", "protein_g": 20, "fibre_g": 6, "sodium_mg": 250, "energy_kcal": 380},
        {"dish_id": "DISH_TOFU_BOWL", "dish_name": "Tofu bowl", "ingredient_id": "ING_RICE", "quantity_per_portion": 100},
    ])
    r = client.post("/api/v1/upload/recipes", files={"file": ("r.csv", rec_df.to_csv(index=False).encode(), "text/csv")},
                    data={"mode": "commit"}, headers=h(MANAGER))
    check("recipe upload", r.status_code == 200 and r.json()["updated"] == 1, r.text)
    tofu = db.recipes.find_one({"dish_id": "DISH_TOFU_BOWL"})
    check("recipe tags computed; uploaded recipe is manager-owned and on the menu", set(tofu["nutrition_tags"]) >= {
        "high_protein", "high_fibre", "lower_sodium"} and tofu["source"] == "manager" and tofu["on_menu"], tofu)
    check("wrong file type rejected", client.post("/api/v1/upload/recipes", files={"file": ("r.txt", b"x", "text/plain")},
                                                  headers=h(MANAGER)).status_code == 400)

    # Forecast
    r = client.post("/api/v1/forecast/run", json={"buffer_percent": 5}, headers=h(MANAGER))
    check("forecast without history ignores idle catalog dishes", r.status_code == 200 and r.json()["method"] == "default_no_history"
          and len(r.json()["dishes"]) < 30, (r.status_code, len(r.json().get("dishes", []))))
    r = client.post("/api/v1/forecast/model/train", headers=h(MANAGER))
    check("training refuses thin history (400)", r.status_code == 400, r.text[:200])
    seed_demo_history(db, weeks=4)
    r = client.post("/api/v1/forecast/run", json={"date": (date.today() + timedelta(days=7)).isoformat()}, headers=h(MANAGER))
    fc = r.json()
    check("forecast with history", r.status_code == 200 and fc["dishes"], r.text[:300])
    check("forecast latest", client.get("/api/v1/forecast/latest", headers=h(MANAGER)).status_code == 200)
    check("employee cannot retrain", client.post("/api/v1/forecast/model/train", headers=h("EMP001")).status_code == 403)
    r = client.post("/api/v1/forecast/model/train", headers=h(MANAGER))
    status = r.json()
    check("train demand models", r.status_code == 200 and status["trained"], r.text[:300])
    check("model status endpoint", client.get("/api/v1/forecast/model", headers=h(MANAGER)).json()["active_models"] == status["active_models"])
    weekday = date.today() + timedelta(days=1)
    while weekday.weekday() >= 5:
        weekday += timedelta(days=1)
    r = client.post("/api/v1/forecast/run", json={"date": weekday.isoformat(), "meal_period": "lunch"}, headers=h(MANAGER))
    fc = r.json()
    expected_method = "random_forest" if status["active_models"] else "same_weekday_average"
    check("forecast uses model only when it beats baseline", r.status_code == 200 and fc["method"] == expected_method
          and fc["dishes"] and all(d["expected_orders"] >= 0 for d in fc["dishes"]), r.text[:300])

    # Dashboards
    r = client.get("/api/v1/dashboard/employee/EMP001", headers=h("EMP001"))
    check("employee dashboard", r.status_code == 200 and r.json()["previous_order"], r.text[:300])
    r = client.get("/api/v1/dashboard/manager", headers=h(MANAGER))
    m = r.json()
    check("manager dashboard", r.status_code == 200 and m["orders_today"] >= 1 and m["average_rating"] == 5, r.text[:400])
    r = client.get("/api/v1/dashboard/executive", headers=h(MANAGER))
    e = r.json()
    check("executive dashboard", r.status_code == 200 and e["operations"]["orders"] > 0 and e["inventory"]["replenishments"] >= 1, r.text[:400])

    # Copilot
    for question, intent in [("Which ingredients are critical?", "inventory_alerts"),
                             ("Which dishes are affected by low paneer stock?", "affected_dishes"),
                             ("What are today's highest-selling dishes?", "top_dishes"),
                             ("What is tomorrow's expected demand?", "forecast"),
                             ("Which healthy categories are increasing?", "healthy_trend"),
                             ("What is the recommendation conversion rate?", "recommendation_conversion")]:
        r = client.post("/api/v1/copilot", json={"question": question}, headers=h(MANAGER))
        check(f"copilot: {intent}", r.status_code == 200 and r.json()["intent"] == intent, r.text[:200])

    # Stock risk: zero spinach -> Palak paneer stockout with a veg swap
    body = b"ingredient_id,name,quantity,unit,reorder_point\nING_SPINACH,Spinach,0,g,1500\n"
    client.post("/api/v1/upload/inventory", files={"file": ("s.csv", body)}, data={"mode": "commit"}, headers=h(MANAGER))
    check("stock risk needs manager", client.get("/api/v1/inventory/risk", headers=h("EMP001")).status_code == 403)
    r = client.get("/api/v1/inventory/risk", headers=h(MANAGER))
    palak = next((d for d in r.json().get("dishes_at_risk", []) if d["dish_id"] == "DISH_PALAK_PANEER"), {})
    check("stock risk flags stockout dish", r.status_code == 200 and palak.get("risk") == "STOCKOUT" and palak.get("limiting_ingredient") == "Spinach", r.text[:400])
    check("stock risk suggests same-diet swap", bool(palak.get("swap_suggestions")), palak)
    check("out-of-stock dish is unavailable but catalog dishes stay orderable", next(i for i in client.get(
        "/api/v1/menu", params={"q": "palak paneer"}, headers=h("EMP001")).json()["items"])["available"] is False)
    r = client.post("/api/v1/copilot", json={"question": "How much revenue are we losing to stockouts?"}, headers=h(MANAGER))
    check("copilot: stock_risk", r.json()["intent"] == "stock_risk" and "Palak" in " ".join(r.json()["evidence"]), r.text[:300])
    forecasts_before = db.forecasts.count_documents({})
    r = client.post("/api/v1/copilot", json={"question": "Predict lunch demand on friday"}, headers=h(MANAGER))
    check("copilot: dynamic forecast", r.json()["intent"] == "forecast" and "lunch" in r.json()["answer"], r.text[:300])
    check("copilot forecast stays read-only", db.forecasts.count_documents({}) == forecasts_before)

    for name in db.list_collection_names():
        db[name].drop()

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
