"""End-to-end smoke test of the ECOS API against a throwaway database (ECOS_test).

Run: ECOS_MONGODB_DB=ECOS_test .venv/bin/python -m backend.smoke_test
"""

import io
import os
import sys
from datetime import date, timedelta

import pandas as pd

assert os.getenv("ECOS_MONGODB_DB", "").endswith("_test"), "Set ECOS_MONGODB_DB=ECOS_test to protect real data"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.core.database import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402

failures: list[str] = []


def check(label: str, condition: bool, detail: object = "") -> None:
    print(("PASS " if condition else "FAIL ") + label + ("" if condition else f" -> {detail}"))
    if not condition:
        failures.append(label)


def h(user_id: str) -> dict:
    return {"X-User-Id": user_id}


with TestClient(app) as client:
    db = get_db()
    for name in db.list_collection_names():
        db[name].drop()
    from backend.app.core.database import ensure_indexes
    from backend.app.core.seed import seed
    ensure_indexes(db)
    seed(db)

    r = client.get("/api/v1/health")
    check("health", r.status_code == 200, r.text)

    # Login: unknown -> employee; manager seeded; manager can't be self-created
    r = client.post("/api/v1/auth/login", json={"user_id": "emp001"})
    check("login new employee", r.status_code == 200 and r.json()["role"] == "employee"
          and r.json()["user_id"] == "EMP001" and not r.json()["profile_complete"], r.text)
    r = client.post("/api/v1/auth/login", json={"user_id": "MGR001"})
    check("login manager", r.json()["role"] == "manager", r.text)
    r = client.post("/api/v1/auth/login", json={"user_id": "bad id!"})
    check("login rejects invalid id", r.status_code == 422, r.status_code)

    # Authorization
    check("users/{id} needs login", client.get("/api/v1/users/EMP001").status_code == 401)
    check("employee cannot read manager dashboard",
          client.get("/api/v1/dashboard/manager", headers=h("EMP001")).status_code == 403)
    client.post("/api/v1/auth/login", json={"user_id": "EMP002"})
    check("employee cannot read other employee",
          client.get("/api/v1/users/EMP001", headers=h("EMP002")).status_code == 403)

    # Preferences
    prefs = {"name": "Riya", "dietary_preference": "vegetarian", "wellness_goals": ["high_protein", "high_fibre"],
             "declared_allergens": ["Peanut"], "favourite_categories": ["indian"], "consented": True}
    r = client.put("/api/v1/users/EMP001/preferences", json={**prefs, "consented": False}, headers=h("EMP001"))
    check("preferences require consent", r.status_code == 400, r.text)
    r = client.put("/api/v1/users/EMP001/preferences", json=prefs, headers=h("EMP001"))
    check("save preferences", r.status_code == 200 and r.json()["profile_complete"], r.text)
    check("get user", client.get("/api/v1/users/EMP001", headers=h("EMP001")).json()["name"] == "Riya")
    users = client.get("/api/v1/users")
    check("list users without auth", users.status_code == 200 and {"EMP001", "MGR001"} <=
          {u["user_id"] for u in users.json()["data"]} and "preferences" not in users.json()["data"][0], users.text)
    r = client.get("/api/v1/wellness/EMP001/monthly", headers=h("EMP001"))
    check("wellness score starts at 20", r.json().get("wellness_score") == 20, r.text[:200])

    # Menu
    r = client.get("/api/v1/menu", params={"meal_period": "lunch", "user_id": "EMP001"})
    lunch = r.json()["items"]
    check("lunch menu published", r.status_code == 200 and len(lunch) >= 5, r.text[:300])
    mutton = next(i for i in lunch if i["dish_id"] == "DISH_MUTTON_BIRYANI")
    check("non-veg flagged ineligible for vegetarian", mutton["eligible"] is False, mutton)

    # Recommendations
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "query": "high protein vegetarian lunch",
                                                     "limit": 5}, headers=h("EMP001"))
    rec = r.json()
    check("recommendations", r.status_code == 200 and rec["items"], r.text[:300])
    check("recommendations exclude non-veg", all(i["diet"] == "veg" for i in rec["items"]), rec["items"])
    check("top recommendation matches a goal", rec["items"][0]["goal_matches"] >= 1, rec["items"][0])
    print("     semantic ranking via Qdrant:", rec["semantic_ranking"], [i["name"] for i in rec["items"]])
    check("recommendations are not stored", "recommendation_event_id" not in rec and
          db.recommendation_events.count_documents({}) == 0)
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "limit": 10,
                                                     "query": "without milk under 120"}, headers=h("EMP001"))
    got = r.json()["items"]
    check("query exclusions and budget applied", got and all("milk" not in i["declared_allergens"] and i["price"] <= 120
                                                              for i in got), got)
    r = client.post("/api/v1/recommendations", json={"meal_period": "lunch", "limit": 2, "exclude_dish_ids":
                                                     [i["dish_id"] for i in rec["items"]]}, headers=h("EMP001"))
    check("exclude_dish_ids gives new dishes", not {i["dish_id"] for i in r.json()["items"]} &
          {i["dish_id"] for i in rec["items"]}, r.text[:300])
    r = client.post("/api/v1/recommendations", json={"query": "peanut free breakfast", "limit": 5}, headers=h("EMP001"))
    check("query can set the meal period", r.json()["meal_period"] == "breakfast", r.text[:300])

    # Order -> stock deduction
    paneer_before = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    order_body = {"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 2}],
                  "recommended_dish_ids": ["DISH_MATAR_PANEER"]}
    r = client.post("/api/v1/orders", json=order_body, headers=h("EMP001"))
    check("place order", r.status_code == 201 and r.json()["total"] == 280, r.text)
    order_id = r.json()["order_id"]
    paneer_after = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    check("paneer deducted 300g", paneer_before - paneer_after == 300, (paneer_before, paneer_after))
    r = client.get("/api/v1/dashboard/employee/EMP001", headers=h("EMP001"))
    check("wellness score +10 per healthy portion", r.json()["wellness_summary"]["wellness_score"] == 40, r.text[:300])
    check("manager cannot order", client.post("/api/v1/orders", json=order_body,
                                              headers=h("MGR001")).status_code == 403)
    r = client.post("/api/v1/orders", json={"items": [{"dish_id": "NOPE", "quantity": 1}]}, headers=h("EMP001"))
    check("unknown dish rejected", r.status_code == 400, r.text)

    # Push paneer to critical, then overdraw
    client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 4}]}, headers=h("EMP002"))
    check("inventory alerts need manager", client.get("/api/v1/inventory/alerts").status_code == 401)
    alerts = client.get("/api/v1/inventory/alerts", headers=h("MGR001")).json()["data"]
    check("paneer critical alert", any(a["ingredient_id"] == "ING_PANEER" and a["status"] == "CRITICAL"
                                       for a in alerts), alerts)
    # 1500 g paneer remains; 11 portions need 1650 g.
    r = client.post("/api/v1/orders", json={"items": [{"dish_id": "DISH_MATAR_PANEER", "quantity": 6},
                                                      {"dish_id": "DISH_MATAR_PANEER", "quantity": 5}]},
                    headers=h("EMP002"))
    check("overdraw rejected with 409", r.status_code == 409, r.text)
    peas = db.ingredients.find_one({"ingredient_id": "ING_PEAS"})["quantity"]
    check("failed order rolled back other ingredients", peas == 6000 - 80 * 6, peas)

    # Affected dishes + movements + replenish
    r = client.get("/api/v1/inventory/ING_PANEER/affected-dishes", headers=h("MGR001"))
    check("affected dishes", {"DISH_MATAR_PANEER", "DISH_PALAK_PANEER"} <= {d["dish_id"] for d in r.json()["data"]}, r.text)
    check("employee cannot replenish", client.post("/api/v1/inventory/ING_PANEER/replenish", json={"quantity": 5000},
                                                   headers=h("EMP001")).status_code == 403)
    r = client.post("/api/v1/inventory/ING_PANEER/replenish", json={"quantity": 5000, "note": "test"}, headers=h("MGR001"))
    check("replenish -> healthy", r.status_code == 200 and r.json()["status"] == "HEALTHY", r.text)
    moves = client.get("/api/v1/inventory/ING_PANEER/movements", headers=h("MGR001")).json()["data"]
    check("movements recorded", {m["type"] for m in moves} >= {"order_consumption", "replenishment"}, moves)
    r = client.patch("/api/v1/inventory/ING_PANEER", json={"reorder_point": 2000}, headers=h("MGR001"))
    check("edit threshold", r.status_code == 200 and r.json()["data"]["reorder_point"] == 2000, r.text)
    r = client.post("/api/v1/inventory", json={"ingredient_id": "ing_ghee", "name": "Ghee", "quantity": 500,
                                               "unit": "g", "reorder_point": 100}, headers=h("MGR001"))
    check("add ingredient", r.status_code == 201, r.text)

    # Order lifecycle
    for status in ("preparing", "ready", "collected"):
        r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": status}, headers=h("MGR001"))
        check(f"status -> {status}", r.status_code == 200, r.text)
    r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"}, headers=h("MGR001"))
    check("cannot cancel collected", r.status_code == 400, r.text)
    emp2_order = client.get("/api/v1/orders", headers=h("EMP002")).json()["data"][0]["order_id"]
    paneer = db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"]
    client.patch(f"/api/v1/orders/{emp2_order}/status", json={"status": "cancelled"}, headers=h("MGR001"))
    check("cancel restores stock", db.ingredients.find_one({"ingredient_id": "ING_PANEER"})["quantity"] == paneer + 600)
    mine = client.get("/api/v1/orders", params={"user_id": "EMP002"}, headers=h("EMP001")).json()["data"]
    check("employee only sees own orders", all(o["user_id"] == "EMP001" for o in mine), mine)
    check("employee cannot open others' order",
          client.get(f"/api/v1/orders/{emp2_order}", headers=h("EMP001")).status_code == 403)

    # Feedback
    r = client.post("/api/v1/feedback", json={"order_id": order_id, "rating": 5, "reason": "taste",
                                              "comment": "Great"}, headers=h("EMP001"))
    check("feedback", r.status_code == 200, r.text)
    check("feedback on others' order 404", client.post("/api/v1/feedback", json={"order_id": emp2_order, "rating": 3},
                                                       headers=h("EMP001")).status_code == 404)

    # Wellness
    r = client.get("/api/v1/wellness/EMP001/monthly", headers=h("EMP001"))
    w = r.json()
    check("wellness monthly", r.status_code == 200 and w["meals_tracked"] == 2
          and w["categories"]["high_protein"]["percentage"] == 100.0, r.text[:400])
    check("wellness recommended tracked", w["recommendation_engagement"]["recommended_meals_ordered"] == 2, w)
    r = client.get("/api/v1/wellness/EMP001/trend", params={"months": 3}, headers=h("EMP001"))
    check("wellness trend", r.status_code == 200 and len(r.json()["trend"]) == 3, r.text)
    check("wellness privacy", client.get("/api/v1/wellness/EMP001/monthly", headers=h("EMP002")).status_code == 403)

    # Menu management
    r = client.post("/api/v1/menu", json={"date": date.today().isoformat(), "meal_period": "snacks",
                                          "dish_ids": ["DISH_SPROUT_CHAAT", "DISH_EGG_SANDWICH"]}, headers=h("MGR001"))
    check("publish menu", r.status_code == 200, r.text)
    menu_id = r.json()["menu_id"]
    r = client.patch(f"/api/v1/menu/{menu_id}/items/DISH_EGG_SANDWICH", json={"paused": True}, headers=h("MGR001"))
    check("pause dish", r.status_code == 200, r.text)
    snacks = client.get("/api/v1/menu", params={"meal_period": "snacks"}).json()["items"]
    check("paused dish unavailable", next(i for i in snacks if i["dish_id"] == "DISH_EGG_SANDWICH")["available"] is False)
    check("recipes list", len(client.get("/api/v1/recipes").json()["data"]) == 13)

    # Uploads
    inv = pd.DataFrame([{"ingredient_id": "ING_TOFU", "name": "Tofu", "quantity": 3000, "unit": "g", "reorder_point": 800}])
    buf = io.BytesIO(); inv.to_excel(buf, index=False); buf.seek(0)
    r = client.post("/api/v1/upload/inventory", files={"file": ("inv.xlsx", buf, "application/octet-stream")},
                    data={"mode": "commit"}, headers=h("MGR001"))
    check("inventory upload", r.status_code == 200 and r.json()["updated"] == 1, r.text)
    bad = pd.DataFrame([{"ingredient_id": "X", "name": "", "quantity": -1, "unit": "g", "reorder_point": 1}])
    r = client.post("/api/v1/upload/inventory", files={"file": ("bad.csv", bad.to_csv(index=False).encode(), "text/csv")},
                    data={"mode": "commit"}, headers=h("MGR001"))
    check("bad inventory upload rejected", r.status_code == 200 and not r.json()["success"] and r.json()["errors"], r.text)
    rec_df = pd.DataFrame([
        {"dish_id": "DISH_TOFU_BOWL", "dish_name": "Tofu bowl", "ingredient_id": "ING_TOFU", "quantity_per_portion": 150,
         "price": 150, "diet": "veg", "meal_periods": "lunch|dinner", "allergens": "soy", "protein_g": 20,
         "fibre_g": 6, "sodium_mg": 250, "energy_kcal": 380},
        {"dish_id": "DISH_TOFU_BOWL", "dish_name": "Tofu bowl", "ingredient_id": "ING_RICE", "quantity_per_portion": 100},
    ])
    r = client.post("/api/v1/upload/recipes", files={"file": ("r.csv", rec_df.to_csv(index=False).encode(), "text/csv")},
                    data={"mode": "commit"}, headers=h("MGR001"))
    check("recipe upload", r.status_code == 200 and r.json()["updated"] == 1, r.text)
    tofu = db.recipes.find_one({"dish_id": "DISH_TOFU_BOWL"})
    check("recipe tags computed", set(tofu["nutrition_tags"]) >= {"high_protein", "high_fibre", "lower_sodium"}, tofu)
    r = client.post("/api/v1/upload/recipes", files={"file": ("r.txt", b"x", "text/plain")}, headers=h("MGR001"))
    check("wrong file type rejected", r.status_code == 400, r.text)

    # Forecast (no history then with history)
    r = client.post("/api/v1/forecast/run", json={"buffer_percent": 5}, headers=h("MGR001"))
    check("forecast no history", r.status_code == 200 and r.json()["method"] == "default_no_history", r.text[:300])
    from backend.app.core.seed import seed_demo_history
    seed_demo_history(db, weeks=4)
    r = client.post("/api/v1/forecast/run", json={"date": (date.today() + timedelta(days=7)).isoformat()},
                    headers=h("MGR001"))
    fc = r.json()
    check("forecast with history", r.status_code == 200 and fc["dishes"], r.text[:300])
    print("     forecast method:", fc["method"], "customers:", fc["expected_customers"], "value:", fc["projected_order_value"])
    check("forecast latest", client.get("/api/v1/forecast/latest", headers=h("MGR001")).status_code == 200)

    # Dashboards
    r = client.get("/api/v1/dashboard/employee/EMP001", headers=h("EMP001"))
    check("employee dashboard", r.status_code == 200 and r.json()["previous_order"], r.text[:300])
    r = client.get("/api/v1/dashboard/manager", headers=h("MGR001"))
    m = r.json()
    check("manager dashboard", r.status_code == 200 and m["orders_today"] >= 1 and m["average_rating"] == 5, r.text[:400])
    r = client.get("/api/v1/dashboard/executive", headers=h("MGR001"))
    e = r.json()
    check("executive dashboard", r.status_code == 200 and e["operations"]["orders"] > 0
          and e["inventory"]["replenishments"] >= 1, r.text[:400])

    # Copilot
    for question, intent in [("Which ingredients are critical?", "inventory_alerts"),
                             ("Which dishes are affected by low paneer stock?", "affected_dishes"),
                             ("What are today's highest-selling dishes?", "top_dishes"),
                             ("What is tomorrow's expected demand?", "forecast"),
                             ("Which healthy categories are increasing?", "healthy_trend"),
                             ("What is the recommendation conversion rate?", "recommendation_conversion")]:
        r = client.post("/api/v1/copilot", json={"question": question}, headers=h("MGR001"))
        check(f"copilot: {intent}", r.status_code == 200 and r.json()["intent"] == intent, r.text[:200])

    # Stock risk: zero spinach -> Palak paneer stockout with a veg swap
    body = b"ingredient_id,name,quantity,unit,reorder_point\nING_SPINACH,Spinach,0,g,1500\n"
    client.post("/api/v1/upload/inventory", files={"file": ("s.csv", body)}, data={"mode": "commit"}, headers=h("MGR001"))
    check("stock risk needs manager", client.get("/api/v1/inventory/risk", headers=h("EMP001")).status_code == 403)
    r = client.get("/api/v1/inventory/risk", headers=h("MGR001"))
    palak = next((d for d in r.json().get("dishes_at_risk", []) if d["dish_id"] == "DISH_PALAK_PANEER"), {})
    check("stock risk flags stockout dish", r.status_code == 200 and palak.get("risk") == "STOCKOUT"
          and palak.get("limiting_ingredient") == "Spinach", r.text[:400])
    check("stock risk suggests same-diet swap", bool(palak.get("swap_suggestions")), palak)
    print("     risk:", r.json()["revenue_at_risk"], r.json()["demand_basis"], palak.get("swap_suggestions"))
    r = client.post("/api/v1/copilot", json={"question": "How much revenue are we losing to stockouts?"}, headers=h("MGR001"))
    check("copilot: stock_risk", r.json()["intent"] == "stock_risk" and "Palak" in " ".join(r.json()["evidence"]), r.text[:300])
    forecasts_before = db.forecasts.count_documents({})
    r = client.post("/api/v1/copilot", json={"question": "Predict lunch demand on friday"}, headers=h("MGR001"))
    check("copilot: dynamic forecast", r.json()["intent"] == "forecast" and ("lunch" in r.json()["answer"]
          or r.json()["source"] == "llm"), r.text[:300])
    check("copilot forecast stays read-only", db.forecasts.count_documents({}) == forecasts_before)
    print("     copilot source:", r.json()["source"], "|", r.json()["answer"][:160])

    for name in db.list_collection_names():
        db[name].drop()

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
