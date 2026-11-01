"""Idempotent demo seed: manager account, ingredients, confirmed recipes, and today's menus."""

import random
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4

from .common import MEAL_PERIODS, now_utc, nutrition_tags, today

MANAGERS = [{"user_id": "MGR001", "name": "Asha Rao", "role": "manager"}]

# (ingredient_id, name, quantity, unit, reorder_point)
INGREDIENTS = [
    ("ING_PANEER", "Paneer", 2400, "g", 1500),
    ("ING_PEAS", "Green peas", 6000, "g", 1500),
    ("ING_SPINACH", "Spinach", 5000, "g", 1500),
    ("ING_RICE", "Basmati rice", 20000, "g", 5000),
    ("ING_MOONG", "Moong dal", 8000, "g", 2000),
    ("ING_RAJMA", "Rajma", 6000, "g", 1500),
    ("ING_MIXDAL", "Mixed dal", 6000, "g", 1500),
    ("ING_TOMATO", "Tomato", 9000, "g", 3000),
    ("ING_ONION", "Onion", 9000, "g", 3000),
    ("ING_MIXVEG", "Mixed vegetables", 8000, "g", 2000),
    ("ING_SEMOLINA", "Semolina", 5000, "g", 1000),
    ("ING_DALIA", "Cracked wheat", 4000, "g", 1000),
    ("ING_MILK", "Milk", 15000, "ml", 4000),
    ("ING_IDLI", "Idli batter", 10000, "g", 2500),
    ("ING_EGG", "Eggs", 180, "pcs", 40),
    ("ING_BREAD", "Whole wheat bread", 120, "slices", 30),
    ("ING_MUTTON", "Mutton", 5000, "g", 1500),
    ("ING_SPROUTS", "Moong sprouts", 3000, "g", 800),
]

INGREDIENT_CATEGORIES = {
    "ING_PANEER": "dairy, cheese", "ING_MILK": "dairy", "ING_PEAS": "vegetable, legume",
    "ING_SPINACH": "leafy green vegetable", "ING_RICE": "grain, cereal", "ING_MOONG": "pulse, lentil, legume",
    "ING_RAJMA": "pulse, kidney bean, legume", "ING_MIXDAL": "pulse, lentil, legume", "ING_TOMATO": "vegetable",
    "ING_ONION": "vegetable", "ING_MIXVEG": "vegetable", "ING_SEMOLINA": "grain, wheat cereal",
    "ING_DALIA": "grain, wheat cereal", "ING_IDLI": "fermented rice and lentil batter", "ING_EGG": "egg, protein",
    "ING_BREAD": "bakery, wheat grain", "ING_MUTTON": "meat, protein", "ING_SPROUTS": "pulse, sprouted legume",
}

# dish_id, name, catalog_code, price, diet, meal_periods, allergens, protein, fibre, sodium, kcal, ingredients
RECIPES = [
    ("DISH_RAVA_DALIA", "Semolina porridge (Rava daliya)", "ASC048", 60, "veg", ["breakfast"],
     ["wheat", "milk"], 10.4, 1.9, 65, 280, [("ING_SEMOLINA", 50), ("ING_MILK", 150)]),
    ("DISH_MEETHA_DALIA", "Cracked wheat porridge", "ASC047", 60, "veg", ["breakfast"],
     ["gluten", "milk"], 10.7, 2.5, 64, 329, [("ING_DALIA", 50), ("ING_MILK", 150)]),
    ("DISH_IDLI", "Steamed idli (3 pcs)", "ASC144", 50, "veg", ["breakfast"],
     [], 6.2, 3.1, 120, 210, [("ING_IDLI", 180)]),
    ("DISH_EGG_BHURJI", "Scrambled egg (Ande ki bhurji)", "ASC059", 70, "egg", ["breakfast"],
     ["egg", "milk"], 13.5, 1.2, 262, 220, [("ING_EGG", 2), ("ING_ONION", 30), ("ING_TOMATO", 30)]),
    ("DISH_MATAR_PANEER", "Matar paneer bowl", "ASC191", 140, "veg", ["lunch", "dinner"],
     ["milk"], 18.3, 9.2, 436, 374, [("ING_PANEER", 150), ("ING_PEAS", 80), ("ING_TOMATO", 60), ("ING_ONION", 40)]),
    ("DISH_PALAK_PANEER", "Palak paneer", "ASC215", 130, "veg", ["lunch", "dinner"],
     ["milk"], 13.9, 5.6, 293, 330, [("ING_PANEER", 120), ("ING_SPINACH", 150), ("ING_ONION", 30)]),
    ("DISH_VEG_BIRYANI", "Vegetable biryani", "ASC123", 120, "veg", ["lunch", "dinner"],
     ["milk"], 9.5, 10.0, 554, 527, [("ING_RICE", 120), ("ING_MIXVEG", 100), ("ING_ONION", 30)]),
    ("DISH_RAJMA", "Rajma curry with rice", "ASC165", 110, "veg", ["lunch"],
     ["milk"], 12.1, 7.0, 425, 420, [("ING_RAJMA", 80), ("ING_RICE", 100), ("ING_TOMATO", 50)]),
    ("DISH_MOONG_DAL", "Moong dal tadka", "ASC151", 80, "veg", ["lunch", "dinner"],
     [], 7.4, 3.2, 280, 139, [("ING_MOONG", 60), ("ING_TOMATO", 30), ("ING_ONION", 20)]),
    ("DISH_MIXED_DAL", "Mixed dal", "ASC155", 80, "veg", ["dinner"],
     ["milk"], 7.5, 4.8, 290, 184, [("ING_MIXDAL", 60), ("ING_TOMATO", 30)]),
    ("DISH_MUTTON_BIRYANI", "Mutton biryani", "ASC122", 220, "non_veg", ["lunch", "dinner"],
     ["milk"], 15.3, 5.0, 546, 396, [("ING_MUTTON", 120), ("ING_RICE", 120), ("ING_ONION", 40)]),
    ("DISH_SPROUT_CHAAT", "Sprouted moong chaat", "ASC170", 50, "veg", ["snacks"],
     [], 7.0, 5.5, 223, 160, [("ING_SPROUTS", 120), ("ING_ONION", 20), ("ING_TOMATO", 20)]),
    ("DISH_EGG_SANDWICH", "Egg sandwich", "ASC024", 60, "egg", ["snacks", "breakfast"],
     ["egg", "wheat"], 12.4, 3.0, 334, 290, [("ING_EGG", 2), ("ING_BREAD", 2)]),
]

# Wikipedia article (or search term) whose lead Wikimedia Commons photo illustrates each dish.
IMAGE_QUERIES = {
    "DISH_RAVA_DALIA": "Upma", "DISH_MEETHA_DALIA": "Dalia porridge", "DISH_IDLI": "Idli",
    "DISH_EGG_BHURJI": "Egg bhurji", "DISH_MATAR_PANEER": "Matar paneer", "DISH_PALAK_PANEER": "Palak paneer",
    "DISH_VEG_BIRYANI": "Vegetable biryani", "DISH_RAJMA": "Rajma", "DISH_MOONG_DAL": "Dal tadka",
    "DISH_MIXED_DAL": "Dal", "DISH_MUTTON_BIRYANI": "Hyderabadi biryani", "DISH_SPROUT_CHAAT": "Chaat",
    "DISH_EGG_SANDWICH": "Egg sandwich",
}


def recipe_documents() -> list[dict[str, Any]]:
    docs = []
    for (dish_id, name, code, price, diet, periods, allergens, protein, fibre, sodium, kcal, lines) in RECIPES:
        units = {ing[0]: ing[3] for ing in INGREDIENTS}
        docs.append({
            "dish_id": dish_id, "name": name, "catalog_code": code, "price": price, "diet": diet,
            "meal_periods": periods, "declared_allergens": allergens,
            "nutrition": {"protein_g": protein, "fibre_g": fibre, "sodium_mg": sodium, "energy_kcal": kcal},
            "nutrition_tags": nutrition_tags(protein, fibre, sodium, kcal),
            "ingredients": [{"ingredient_id": i, "quantity": q, "unit": units[i]} for i, q in lines],
            "evidence_status": "confirmed", "image_query": IMAGE_QUERIES.get(dish_id), "updated_at": now_utc(),
        })
    return docs


def ensure_menus(db: Any, for_date: str) -> None:
    """Publish a default menu for each meal period when none exists for the date."""
    for period in MEAL_PERIODS:
        if db.menus.find_one({"date": for_date, "meal_period": period}):
            continue
        dish_ids = [r["dish_id"] for r in db.recipes.find({"meal_periods": period, "evidence_status": "confirmed"})]
        if dish_ids:
            db.menus.insert_one({
                "menu_id": f"MENU-{for_date}-{period}", "date": for_date, "meal_period": period,
                "dish_ids": dish_ids, "paused_dish_ids": [], "published": True, "updated_at": now_utc(),
            })


def seed(db: Any) -> None:
    for manager in MANAGERS:
        db.users.update_one({"user_id": manager["user_id"]},
                            {"$setOnInsert": {**manager, "profile_complete": True, "preferences": {},
                                              "created_at": now_utc()}}, upsert=True)
    if db.ingredients.count_documents({}) == 0:
        db.ingredients.insert_many([
            {"ingredient_id": i, "name": n, "quantity": q, "unit": u, "reorder_point": r,
             "category": INGREDIENT_CATEGORIES.get(i, ""), "updated_at": now_utc()}
            for i, n, q, u, r in INGREDIENTS
        ])
    for ingredient_id, category in INGREDIENT_CATEGORIES.items():
        db.ingredients.update_one({"ingredient_id": ingredient_id, "category": {"$exists": False}},
                                  {"$set": {"category": category}})
    if db.recipes.count_documents({}) == 0:
        db.recipes.insert_many(recipe_documents())
    for dish_id, query in IMAGE_QUERIES.items():
        db.recipes.update_one({"dish_id": dish_id, "image_query": {"$exists": False}},
                              {"$set": {"image_query": query}, "$unset": {"image_url": ""}})
    ensure_menus(db, today())


def seed_demo_history(db: Any, weeks: int = 8) -> int:
    """Create past collected orders (source=demo_seed) so forecasts and trends have history."""
    recipes = {r["dish_id"]: r for r in db.recipes.find({})}
    rng = random.Random(42)
    users = [f"DEMO{n:03d}" for n in range(1, 31)]
    for user_id in users:
        db.users.update_one({"user_id": user_id}, {"$setOnInsert": {
            "user_id": user_id, "name": f"Demo employee {user_id[-3:]}", "role": "employee",
            "preferences": {"dietary_preference": "vegetarian", "wellness_goals": ["high_protein"],
                            "declared_allergens": []},
            "profile_complete": True, "created_at": now_utc()}}, upsert=True)
    orders = []
    start = date.today() - timedelta(weeks=weeks)
    for offset in range(weeks * 7):
        day = start + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        for period, hour in (("breakfast", 9), ("lunch", 13), ("snacks", 16), ("dinner", 19)):
            options = [d for d, r in recipes.items() if period in r["meal_periods"]]
            customers = rng.sample(users, k=rng.randint(6, 14) if period == "lunch" else rng.randint(2, 7))
            for user_id in customers:
                dish = recipes[rng.choice(options)]
                created = datetime.combine(day, time(hour, rng.randint(0, 59)), tzinfo=timezone.utc)
                orders.append({
                    "order_id": f"ORD-{uuid4().hex[:10].upper()}", "pickup_reference": "H000",
                    "user_id": user_id, "date": day.isoformat(), "meal_period": period,
                    "items": [{"dish_id": dish["dish_id"], "name": dish["name"], "quantity": 1,
                               "unit_price": dish["price"], "line_total": dish["price"],
                               "nutrition_tags": dish["nutrition_tags"], "recommended": rng.random() < 0.4}],
                    "total": dish["price"], "status": "collected", "created_at": created,
                    "collected_at": created + timedelta(minutes=rng.randint(8, 20)), "source": "demo_seed",
                })
    if orders:
        db.orders.insert_many(orders)
    return len(orders)
