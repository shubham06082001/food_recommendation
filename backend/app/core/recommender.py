"""Real-time recommendation engine. Nothing is stored: every call re-reads the live menu, stock,
profile, order history and ratings, and understands the free-text query (tags, budget, exclusions)."""

import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from .common import MEAL_PERIODS, eligibility
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


def _has(text: str, word: str, prefix: bool = False) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}" + ("" if prefix else r"s?\b"), text))


def parse_query(text: str) -> dict[str, Any]:
    """Turn free text like 'light high protein dinner under 150 without paneer' into structured intent."""
    q = " " + re.sub(r"[^a-z0-9 ]+", " ", text.lower().replace("₹", " rs ")) + " "
    excluded: set[str] = set()
    for pattern in (r"\b(?:without|no|avoid|except|excluding|allergic to|free of)\s+(?:any\s+)?([a-z]+)",
                    r"\b([a-z]+)\s+free\b"):
        for word in re.findall(pattern, q):
            if word not in {"preference", "salt", "sodium", "added"}:
                excluded.add(word)
    allergens = {a for w in excluded for key, group in ALLERGEN_ALIASES.items() if w.startswith(key) for a in group}
    price = re.search(r"\b(?:under|below|less than|within|upto|up to|max|budget|around)\s*(?:rs|inr)?\s*(\d{2,4})\b", q)
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
    week = (date.today() - timedelta(days=14)).isoformat()
    for order in db.orders.find({"date": {"$gte": week}, "status": {"$ne": "cancelled"}}, {"items": 1}):
        for item in order["items"]:
            popular[item["dish_id"]] += item["quantity"]
    return counts, last, {d: sum(r) / len(r) for d, r in ratings.items()}, popular


def recommend(db: Any, user: dict[str, Any], query: str, meal_period: str | None, limit: int,
              exclude_dish_ids: list[str]) -> dict[str, Any]:
    prefs = user.get("preferences", {})
    goals = [g for g in prefs.get("wellness_goals", []) if g in TAG_LABELS]
    diet = (prefs.get("dietary_preference") or "no_preference").replace("_", " ")
    intent = parse_query(query)
    period = intent["meal_period"] or meal_period

    names = {i["ingredient_id"]: i["name"].lower() for i in db.ingredients.find({}, {"ingredient_id": 1, "name": 1})}
    pool: dict[str, dict[str, Any]] = {}
    for item in sorted(menu_items(db, period), key=lambda i: i["meal_period"] != period):
        pool.setdefault(item["dish_id"], item)

    own_allergens = {a.lower() for a in prefs.get("declared_allergens", [])}
    blocked_allergens = own_allergens | set(intent["excluded_allergens"])
    excluded_ids, candidates, rejected = set(exclude_dish_ids), [], Counter()
    for item in pool.values():
        text = " ".join([item["name"].lower(), *(names.get(i["ingredient_id"], "") for i in item["ingredients"])])
        kcal = item.get("nutrition", {}).get("energy_kcal", 0)
        declared = {a.lower() for a in item.get("declared_allergens", [])}
        reason = (
            "unavailable" if not item["available"] else
            "seen" if item["dish_id"] in excluded_ids else
            "diet or allergen" if not eligibility(item, prefs)[0] else
            "allergen" if declared & blocked_allergens or any(_has(text, a) for a in blocked_allergens) else
            "excluded" if any(_has(text, t, True) for t in intent["excluded_terms"]) else
            "diet" if (intent["veg_only"] and item.get("diet") != "veg")
            or (intent["vegan"] and declared & ANIMAL_ALLERGENS) else
            "budget" if intent["max_price"] and item["price"] > intent["max_price"] else
            "calories" if (intent["max_kcal"] and kcal > intent["max_kcal"])
            or (intent["min_kcal"] and kcal < intent["min_kcal"]) else "")
        if reason:
            rejected[reason] += 1
            continue
        candidates.append((item, text, [t for t in intent["terms"] if _has(text, t, True)]))

    base = query.strip() or " ".join([diet, *(TAG_LABELS[g] for g in goals), "Indian", period or "meal"])
    scores = semantic_scores(base, [c[0]["catalog_code"] for c in candidates if c[0].get("catalog_code")])
    top_semantic = max(scores.values(), default=0) or 1
    counts, last, ratings, popular = _history(db, user["user_id"])
    top_popular = max(popular.values(), default=0) or 1

    exact = [c for c in candidates if c[2]] if intent["terms"] else candidates
    note = ""
    if intent["terms"] and not exact:
        note = f"No dish matches “{' '.join(intent['terms'])}” exactly; showing the closest options for you."
        exact = candidates
    ranked = []
    for item, text, matched_terms in exact:
        tags = set(item.get("nutrition_tags", []))
        goal_hits = [g for g in goals if g in tags]
        query_hits = [t for t in intent["tags"] if t in tags]
        semantic = scores.get(item.get("catalog_code"), 0.0)
        age = (date.today() - last[item["dish_id"]]).days if item["dish_id"] in last else None
        favourite = [c for c in prefs.get("favourite_categories", []) if _has(text, c, True)]
        score = (0.30 * semantic / top_semantic
                 + 0.30 * (len(matched_terms) / len(intent["terms"]) if intent["terms"] else 0)
                 + 0.20 * (len(goal_hits) / len(goals) if goals else 0)
                 + 0.30 * (len(query_hits) / len(intent["tags"]) if intent["tags"] else 0)
                 + (0.10 if intent["wants_meat"] and item.get("diet") == "non_veg" else 0)
                 + 0.05 * bool(favourite)
                 + 0.03 * min(counts[item["dish_id"]], 3) + 0.05 * (ratings.get(item["dish_id"], 3) - 3) / 2
                 - (0.12 if age is not None and age <= 1 else 0)
                 + 0.05 * popular[item["dish_id"]] / top_popular
                 - (0.05 if item["maximum_portions"] < 5 else 0))
        reasons = [f"Matches your {TAG_LABELS[g]} goal" for g in goal_hits]
        reasons += [f"{TAG_LABELS[t].capitalize()} as you asked" for t in query_hits if t not in goal_hits]
        reasons += [f"Matches “{t}”" for t in matched_terms[:2]]
        if intent["max_price"]:
            reasons.append(f"Within your ₹{intent['max_price']:.0f} budget")
        if ratings.get(item["dish_id"], 0) >= 4:
            reasons.append("You rated this highly before")
        elif counts[item["dish_id"]] >= 2:
            reasons.append(f"One of your regulars ({counts[item['dish_id']]} orders)")
        elif age is None and counts[item["dish_id"]] == 0 and not query.strip():
            reasons.append("Something new to try")
        if popular[item["dish_id"]] >= 0.7 * top_popular and popular[item["dish_id"]] > 0:
            reasons.append("Popular this fortnight")
        if own_allergens:
            reasons.append(f"Free of your declared allergens ({', '.join(sorted(own_allergens))})")
        if diet not in ("no preference", ""):
            reasons.append(f"Fits your {diet} preference")
        if item["maximum_portions"] < 5:
            reasons.append(f"Only {item['maximum_portions']} portions left")
        ranked.append({
            "dish_id": item["dish_id"], "name": item["name"], "price": item["price"], "meal_period": item["meal_period"],
            "nutrition": item.get("nutrition", {}), "nutrition_tags": sorted(tags),
            "declared_allergens": item.get("declared_allergens", []), "diet": item.get("diet"),
            "maximum_portions": item["maximum_portions"], "semantic_score": semantic,
            "goal_matches": len(goal_hits), "match_percent": max(0, min(99, round(score * 100 + 40))),
            "reasons": reasons[:5], "_score": score})
    ranked.sort(key=lambda r: r["_score"], reverse=True)
    items = [{k: v for k, v in r.items() if k != "_score"} for r in ranked[:limit]]
    return {
        "query": query.strip() or base, "meal_period": period, "semantic_ranking": bool(scores),
        "interpreted": {k: v for k, v in intent.items() if v and k not in ("terms", "meal_period")},
        "filtered_out": dict(rejected), "total_matches": len(ranked), "has_more": len(ranked) > limit,
        "note": note, "items": items,
    }
