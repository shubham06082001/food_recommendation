"""Manager view of how today's orders drew down inventory, with Qdrant semantic focus (e.g. 'dairy')."""

from collections import Counter, defaultdict
from datetime import date as Date
from typing import Any

from fastapi import APIRouter, Depends, Query

from ..core.common import require_manager, serialize, stock_status
from ..core.database import get_db
from ..core.menu import max_portions, stock_map
from ..core.semantic import ingredient_scores

router = APIRouter()


def _focus(query: str, texts: dict[str, str]) -> tuple[dict[str, float], bool]:
    """Ingredients that best match the query: Qdrant similarity, else plain name/category matching."""
    scores = ingredient_scores(query, texts)
    if scores:
        top = max(scores.values())
        ranked = sorted(scores.items(), key=lambda s: -s[1])
        return {k: v for k, v in ranked[:6] if v >= max(0.25, 0.75 * top)}, True
    words = query.lower().split()
    return {k: 1.0 for k, n in texts.items() if any(w in n.lower() for w in words)}, False


@router.get("/inventory/consumption")
def consumption(date: Date | None = None, query: str = Query(default="", max_length=100),
                _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    day = (date or Date.today()).isoformat()
    orders = list(db.orders.find({"date": day}).sort("created_at", -1))
    stock = stock_map(db)
    names = {k: v["name"] for k, v in stock.items()}
    used: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for move in db.inventory_movements.find({"order_id": {"$in": [o["order_id"] for o in orders]},
                                             "type": {"$in": ["order_consumption", "order_cancelled"]}}):
        used[move["order_id"]][move["ingredient_id"]] += -float(move["quantity"])

    focus, semantic = ({}, False)
    if query.strip():
        texts = {k: f"{v['name']}, {v.get('category') or 'food'} ingredient" for k, v in stock.items()}
        focus, semantic = _focus(query, texts)
    net: Counter = Counter()
    touched: Counter = Counter()
    rows = []
    for order in orders:
        lines = {k: round(v, 2) for k, v in used[order["order_id"]].items() if v}
        net.update(lines)
        touched.update(lines.keys())
        if focus and not set(lines) & set(focus):
            continue
        rows.append({
            "order_id": order["order_id"], "pickup_reference": order.get("pickup_reference"),
            "user_id": order["user_id"], "status": order["status"], "meal_period": order.get("meal_period"),
            "time": serialize(order)["created_at"][11:16],
            "dishes": [f"{i['name']} × {i['quantity']}" for i in order["items"]],
            "ingredients": [{"ingredient_id": k, "name": names.get(k, k), "quantity": q,
                             "unit": stock.get(k, {}).get("unit", "")} for k, q in sorted(lines.items(), key=lambda x: -x[1])],
        })

    ingredients = []
    for ingredient_id, amount in net.items():
        if focus and ingredient_id not in focus:
            continue
        item = stock.get(ingredient_id, {})
        remaining = float(item.get("quantity", 0))
        before = remaining + amount
        ingredients.append({
            "ingredient_id": ingredient_id, "name": names.get(ingredient_id, ingredient_id), "unit": item.get("unit", ""),
            "used_today": round(amount, 2), "orders": touched[ingredient_id], "remaining": remaining,
            "depletion_pct": round(100 * amount / before, 1) if before > 0 else 0.0,
            "status": stock_status(item) if item else "STOCKOUT", "match_score": focus.get(ingredient_id)})
    ingredients.sort(key=lambda i: (-(i["match_score"] or 0), -i["depletion_pct"]))

    # Portions each dish could make before today's orders vs now shows which dishes lost the most headroom.
    before_stock = {k: {**v, "quantity": float(v.get("quantity", 0)) + net.get(k, 0)} for k, v in stock.items()}
    relevant = set(focus) or set(net)
    affected = []
    for recipe in db.recipes.find({"ingredients.ingredient_id": {"$in": list(relevant)}}):
        start, now = max_portions(recipe, before_stock), max_portions(recipe, stock)
        if start > now or focus:
            affected.append({"dish_id": recipe["dish_id"], "name": recipe["name"], "portions_before": start,
                             "portions_now": now, "portions_lost": start - now,
                             "lost_pct": round(100 * (start - now) / start, 1) if start else 0.0,
                             "ingredients": [names.get(l["ingredient_id"], l["ingredient_id"])
                                             for l in recipe["ingredients"] if l["ingredient_id"] in relevant]})
    affected.sort(key=lambda d: (-d["lost_pct"], d["portions_now"]))

    return {
        "date": day, "query": query, "semantic_search": semantic,
        "matched_ingredients": [{"ingredient_id": k, "name": names.get(k, k), "score": v}
                                for k, v in sorted(focus.items(), key=lambda x: -x[1])],
        "totals": {"orders": len(orders), "orders_shown": len(rows),
                   "portions": sum(i["quantity"] for o in orders for i in o["items"] if o["status"] != "cancelled"),
                   "ingredients_used": len(ingredients)},
        "ingredients": ingredients, "affected_dishes": affected[:12], "orders": rows,
    }
