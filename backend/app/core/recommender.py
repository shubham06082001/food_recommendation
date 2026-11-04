"""Real-time recommendation engine. Nothing is stored: every call re-reads the live menu, stock,
profile, order history and ratings, and understands the free-text query (tags, budget, exclusions)."""

import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from .common import MEAL_PERIODS, allergen_set, eligibility
from .menu import menu_items
from .semantic import semantic_scores

TAG_LABELS = {"high_protein": "high-protein", "high_fibre": "high-fibre",
              "lower_sodium": "lower-sodium", "balanced": "balanced"}
TAG_PATTERNS = {
    "high_protein": r"protein|muscle|gym|workout",
    "high_fibre": r"fib(?:re|er)|digest",
    "lower_sodium": r"low(?:er)? (?:sodium|salt)|less salt|sodium|\bbp\b|blood pressure",
    "balanced": r"balanced|healthy|nutritious|wholesome",
}
ALLERGEN_ALIASES = {
    "nut": {"peanut", "tree nuts"}, "peanut": {"peanut"}, "dairy": {"milk"}, "milk": {"milk"}, "lactose": {"milk"},
    "gluten": {"gluten", "wheat"}, "wheat": {"wheat", "gluten"}, "egg": {"egg"}, "soy": {"soy"},
    "fish": {"fish"}, "sesame": {"sesame"}, "mustard": {"mustard"},
}
ANIMAL_ALLERGENS = {"milk", "dairy", "egg"}
STOP = set("""a an the and or for with without want need some something anything give show me my i we please food
meal meals dish dishes eat eating have get any under below than less within upto max budget rs inr cheap light
filling heavy hearty low high lunch dinner breakfast snack snacks today now indian veg vegetarian vegan non protein
fibre fiber salt sodium balanced healthy nutritious tasty good best option options calorie calories cal diet free
avoid except excluding no allergic of to""".split())
NEGATION = (r"\b(?:without|no|avoid|except|excluding|allergic to|free of)\s+(?:any\s+)?([a-z]+(?:\s+(?:and|or)\s+[a-z]+){0,3})",
            r"\b([a-z]+)\s+free\b")
PRICE = r"\b(?:under|below|less than|within|upto|up to|max|budget|around)\s{0,3}(?:rs|inr)?\s{0,3}(\d{2,4})\b"
SEMANTIC_FLOOR = 0.35  # A non-literal match must be at least this similar...
SEMANTIC_SHARE = 0.8   # ...and within this share of the best similarity.


def _has(text: str, word: str, prefix: bool = False) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}" + ("" if prefix else r"s?\b"), text))


def parse_query(text: str) -> dict[str, Any]:
    """Turn free text like 'light high protein dinner under 150 without paneer' into structured intent."""
    q = " " + re.sub(r"[^a-z0-9 ]+", " ", text.lower().replace("₹", " rs ")) + " "
    words = {w for pattern in NEGATION for found in re.findall(pattern, q) for w in re.split(r"\s+(?:and|or)\s+", found)}
    excluded = words - {"preference", "salt", "sodium", "added"} - STOP
    allergens = {a for w in excluded for key, group in ALLERGEN_ALIASES.items() if w.startswith(key) for a in group}
    price = re.search(PRICE, q)
    intent: dict[str, Any] = {
        "tags": [t for t, p in TAG_PATTERNS.items() if re.search(p, q)],
        "excluded_terms": sorted(excluded), "excluded_allergens": sorted(allergens),
        "max_price": float(price.group(1)) if price else None,
        "max_kcal": 350 if re.search(r"\b(light|low cal(?:orie)?s?|diet)\b", q) else None,
        "min_kcal": 400 if re.search(r"\b(filling|heavy|hearty|full meal)\b", q) else None,
        "veg_only": bool(re.search(r"\b(vegan|veg|vegetarian)\b", q)) and " non veg" not in q,
        "vegan": " vegan " in q,
        "wants_meat": bool(re.search(r"\b(non veg|nonveg|chicken|mutton|meat)\b", q)),
        "meal_period": next((p for p in MEAL_PERIODS if re.search(rf"\b{p}\b|\b{p.rstrip('s')}\b", q)), None),
    }
    intent["terms"] = [t for t in re.findall(r"[a-z]{3,}", q) if t not in STOP and t not in excluded]
    return intent


def _history(db: Any, user_id: str) -> tuple[Counter, dict[str, date], dict[str, float], Counter]:
    """Per-user dish counts, last-ordered dates, average ratings, plus fortnight popularity across everyone."""
    since = (date.today() - timedelta(days=45)).isoformat()
    counts: Counter = Counter()
    last: dict[str, date] = {}
    order_dishes: dict[str, list[str]] = {}
    for order in db.orders.find({"user_id": user_id, "status": {"$ne": "cancelled"}, "date": {"$gte": since}}):
        ids = [i["dish_id"] for i in order["items"]]
        order_dishes[order["order_id"]] = ids
        for dish_id in ids:
            counts[dish_id] += 1
            last[dish_id] = max(last.get(dish_id, date.min), date.fromisoformat(order["date"]))
    ratings: dict[str, list[int]] = defaultdict(list)
    for feedback in db.feedback.find({"user_id": user_id}):
        for dish_id in order_dishes.get(feedback["order_id"], []):
            ratings[dish_id].append(feedback["rating"])
    popular: Counter = Counter()
    fortnight = (date.today() - timedelta(days=14)).isoformat()
    for order in db.orders.find({"date": {"$gte": fortnight}, "status": {"$ne": "cancelled"}}, {"items": 1}):
        for item in order["items"]:
            popular[item["dish_id"]] += item["quantity"]
    return counts, last, {d: sum(r) / len(r) for d, r in ratings.items()}, popular


def _reject_reason(item: dict[str, Any], text: str, prefs: dict[str, Any], intent: dict[str, Any],
                   blocked: set[str], seen: set[str]) -> str:
    """Why a dish is excluded ('' = keep). Allergen, diet and budget rules are hard filters, never ranking hints."""
    declared = allergen_set(item.get("declared_allergens"))
    kcal = item.get("nutrition", {}).get("energy_kcal", 0)
    if not item["available"]:
        return "unavailable"
    if item["dish_id"] in seen:
        return "seen"
    if item.get("component") and not intent["terms"]:
        return "side item"
    if not eligibility(item, prefs)[0]:
        return "diet or allergen"
    if declared & blocked or any(_has(text, a) for a in blocked):
        return "allergen"
    if any(_has(text, t, True) for t in intent["excluded_terms"]):
        return "excluded"
    if (intent["veg_only"] and item.get("diet") != "veg") or (intent["vegan"] and declared & ANIMAL_ALLERGENS):
        return "diet"
    if intent["max_price"] and item["price"] > intent["max_price"]:
        return "budget"
    if (intent["max_kcal"] and kcal > intent["max_kcal"]) or (intent["min_kcal"] and kcal < intent["min_kcal"]):
        return "calories"
    return ""


def _reasons(item: dict, goal_hits: list[str], query_hits: list[str], matched: list[str], ctx: dict[str, Any]) -> list[str]:
    dish_id, intent, prefs = item["dish_id"], ctx["intent"], ctx["prefs"]
    count, rating, popular = ctx["counts"][dish_id], ctx["ratings"].get(dish_id, 0), ctx["popular"][dish_id]
    reasons = [f"Matches your {TAG_LABELS[g]} goal" for g in goal_hits]
    reasons += [f"{TAG_LABELS[t].capitalize()} as you asked" for t in query_hits if t not in goal_hits]
    reasons += [f"Matches “{t}”" for t in matched[:2]]
    if intent["max_price"]:
        reasons.append(f"Within your ₹{intent['max_price']:.0f} budget")
    if rating >= 4:
        reasons.append("You rated this highly before")
    elif count >= 2:
        reasons.append(f"One of your regulars ({count} orders)")
    elif count == 0 and not ctx["query"]:
        reasons.append("Something new to try")
    if popular and popular >= 0.7 * ctx["top_popular"]:
        reasons.append("Popular this fortnight")
    if ctx["own_allergens"]:
        reasons.append(f"Free of your declared allergens ({', '.join(sorted(ctx['own_allergens']))})")
    if ctx["diet"] not in ("no preference", ""):
        reasons.append(f"Fits your {ctx['diet']} preference")
    if item["maximum_portions"] < 5:
        reasons.append(f"Only {item['maximum_portions']} portions left")
    return reasons[:5]


def _score(item: dict, text: str, matched: list[str], goal_hits: list[str], query_hits: list[str], ctx: dict[str, Any]) -> float:
    dish_id, intent, prefs, goals = item["dish_id"], ctx["intent"], ctx["prefs"], ctx["goals"]
    terms = intent["terms"]
    last = ctx["last"].get(dish_id)
    recently = last is not None and (date.today() - last).days <= 1
    favourite = any(_has(text, c, True) for c in prefs.get("favourite_categories", []))
    return (0.30 * ctx["scores"].get(item.get("catalog_code"), 0.0) / ctx["top_semantic"]
            + 0.30 * (len(matched) / len(terms) if terms else 0)
            + 0.20 * (len(goal_hits) / len(goals) if goals else 0)
            + 0.30 * (len(query_hits) / len(intent["tags"]) if intent["tags"] else 0)
            + (0.10 if intent["wants_meat"] and item.get("diet") == "non_veg" else 0)
            + 0.05 * favourite
            + 0.03 * min(ctx["counts"][dish_id], 3) + 0.05 * (ctx["ratings"].get(dish_id, 3) - 3) / 2
            - (0.12 if recently else 0)
            + 0.05 * ctx["popular"][dish_id] / ctx["top_popular"]
            - (0.05 if item["maximum_portions"] < 5 else 0))


def recommend(db: Any, user: dict[str, Any], query: str, meal_period: str | None, limit: int,
              exclude_dish_ids: list[str], period_from_query: bool = True, offset: int = 0) -> dict[str, Any]:
    prefs = user.get("preferences", {})
    goals = [g for g in prefs.get("wellness_goals", []) if g in TAG_LABELS]
    diet = (prefs.get("dietary_preference") or "no_preference").replace("_", " ")
    intent = parse_query(query)
    period = (period_from_query and intent["meal_period"]) or meal_period
    query = query.strip()

    names = {i["ingredient_id"]: i["name"].lower() for i in db.ingredients.find({}, {"ingredient_id": 1, "name": 1})}
    pool = {item["dish_id"]: item for item in menu_items(db, period, light=True)}

    own_allergens = allergen_set(prefs.get("declared_allergens"))
    blocked = own_allergens | allergen_set(intent["excluded_allergens"])
    candidates, rejected = [], Counter()
    for item in pool.values():
        text = " ".join([item["name"].lower(), item.get("ingredient_text", ""),
                         *(names.get(i["ingredient_id"], "") for i in item.get("ingredients", []))])
        reason = _reject_reason(item, text, prefs, intent, blocked, set(exclude_dish_ids))
        if reason:
            rejected[reason] += 1
        else:
            candidates.append((item, text, [t for t in intent["terms"] if _has(text, t, True)]))

    base = query or " ".join([diet, *(TAG_LABELS[g] for g in goals), "Indian", period or "meal"])
    scores = semantic_scores(base, [c[0]["catalog_code"] for c in candidates if c[0].get("catalog_code")])
    counts, last, ratings, popular = _history(db, user["user_id"])
    ctx = {"intent": intent, "prefs": prefs, "goals": goals, "diet": diet, "own_allergens": own_allergens,
           "query": query, "scores": scores, "top_semantic": max(scores.values(), default=0) or 1,
           "counts": counts, "last": last, "ratings": ratings, "popular": popular,
           "top_popular": max(popular.values(), default=0) or 1}

    matches = candidates
    if intent["terms"]:  # Literal word hits plus close semantic matches (e.g. 'cottage cheese' for 'paneer').
        cutoff = max(SEMANTIC_FLOOR, SEMANTIC_SHARE * ctx["top_semantic"]) if scores else float("inf")
        matches = [c for c in candidates if c[2] or scores.get(c[0].get("catalog_code"), 0.0) >= cutoff]
    note = ""
    if intent["terms"] and not matches:
        note = f"No dish matches “{' '.join(intent['terms'])}” exactly; showing the closest options for you."
        matches = candidates
    ranked = []
    for item, text, matched in matches:
        tags = set(item.get("nutrition_tags", []))
        goal_hits = [g for g in goals if g in tags]
        query_hits = [t for t in intent["tags"] if t in tags]
        score = _score(item, text, matched, goal_hits, query_hits, ctx)
        ranked.append({
            "dish_id": item["dish_id"], "name": item["name"], "price": item["price"], "meal_period": item["meal_period"],
            "nutrition": item.get("nutrition", {}), "nutrition_tags": sorted(tags),
            "declared_allergens": item.get("declared_allergens", []), "diet": item.get("diet"),
            "maximum_portions": item["maximum_portions"], "semantic_score": scores.get(item.get("catalog_code"), 0.0),
            "image_url": item.get("image_url", ""), "image_credit": item.get("image_credit", ""),
            "nutrient_profile": item.get("nutrient_profile"),
            "goal_matches": len(goal_hits), "match_percent": max(0, min(99, round(score * 100 + 40))),
            "reasons": _reasons(item, goal_hits, query_hits, matched, ctx), "_score": score})
    ranked.sort(key=lambda r: r["_score"], reverse=True)
    page = ranked[offset:offset + limit]
    profiles = {r["dish_id"]: r.get("nutrient_profile") for r in db.recipes.find(
        {"dish_id": {"$in": [p["dish_id"] for p in page]}}, {"dish_id": 1, "nutrient_profile": 1})}
    for row in page:
        row["nutrient_profile"] = profiles.get(row["dish_id"])
    return {
        "query": query or base, "meal_period": period, "semantic_ranking": bool(scores),
        "interpreted": {k: v for k, v in intent.items() if v and k not in ("terms", "meal_period")},
        "filtered_out": dict(rejected), "total_matches": len(ranked), "offset": offset,
        "has_more": len(ranked) > offset + limit, "note": note,
        "items": [{k: v for k, v in r.items() if k != "_score"} for r in page],
    }


def meal_plan(db: Any, user: dict[str, Any], query: str) -> dict[str, Any]:
    """Best live pick per meal period (no repeats) with day totals against daily reference values."""
    from .enrich import DAILY_REFERENCE, MACROS, MICROS

    picks, chosen = [], []
    for period in MEAL_PERIODS:
        result = recommend(db, user, query, period, 1, chosen, period_from_query=False)
        if result["items"]:
            chosen.append(result["items"][0]["dish_id"])
            picks.append({"meal_period": period, **result["items"][0]})
    totals: dict[str, float] = defaultdict(float)
    for pick in picks:
        profile = pick.get("nutrient_profile") or {}
        rows = profile.get("macros", []) + profile.get("micros", [])
        if not rows:
            rows = [{"key": k, "amount": v} for k, v in pick["nutrition"].items()]
        for row in rows:
            totals[row["key"]] += row["amount"]

    def summary(spec: dict) -> list[dict[str, Any]]:
        return [{"key": k, "label": label, "unit": unit, "amount": round(totals[k], 1),
                 "daily_pct": round(100 * totals[k] / DAILY_REFERENCE[k], 1)} for k, (label, unit) in spec.items()]
    return {"query": query, "meals": picks, "totals": {"price": sum(p["price"] for p in picks),
                                                    "macros": summary(MACROS), "micros": summary(MICROS)}}
