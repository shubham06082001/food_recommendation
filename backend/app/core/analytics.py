"""KPI aggregations shared by dashboards and the copilot."""

from collections import Counter
from datetime import date, timedelta
from typing import Any

from .common import pct, stock_status

ACTIVE = ["confirmed", "preparing", "ready"]
HEALTHY = {"high_protein", "high_fibre", "lower_sodium", "balanced"}


def order_kpis(orders: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [o for o in orders if o["status"] != "cancelled"]
    collected = [o for o in valid if o["status"] == "collected"]
    portions = sum(i["quantity"] for o in valid for i in o["items"])
    healthy = sum(i["quantity"] for o in valid for i in o["items"] if HEALTHY & set(i.get("nutrition_tags", [])))
    recommended = sum(i["quantity"] for o in valid for i in o["items"] if i.get("recommended"))
    dishes = Counter()
    for order in valid:
        for item in order["items"]:
            dishes[item["name"]] += item["quantity"]
    durations = [(o["collected_at"] - o["created_at"]).total_seconds() / 60 for o in collected
                 if o.get("collected_at") and o.get("created_at")]
    accepted_value = sum(o["total"] for o in valid)
    return {
        "orders": len(valid), "cancelled_orders": len(orders) - len(valid),
        "active_orders": sum(o["status"] in ACTIVE for o in valid), "collected_orders": len(collected),
        "customers": len({o["user_id"] for o in valid}), "portions": portions,
        "accepted_order_value": round(accepted_value, 2),
        "collected_order_value": round(sum(o["total"] for o in collected), 2),
        "average_order_value": round(accepted_value / len(valid), 2) if valid else 0,
        "healthy_meal_adoption": pct(healthy, portions),
        "recommendation_share": pct(recommended, portions),
        "fulfilment_rate": pct(len(collected), len(valid)),
        "average_completion_minutes": round(sum(durations) / len(durations), 1) if durations else None,
        "top_dishes": [{"name": n, "portions": q} for n, q in dishes.most_common(5)],
        "status_counts": dict(Counter(o["status"] for o in orders)),
    }


def inventory_kpis(db: Any) -> dict[str, Any]:
    items = list(db.ingredients.find({}, {"_id": 0}))
    statuses = Counter(stock_status(i) for i in items)
    alerts = sorted(({"ingredient_id": i["ingredient_id"], "name": i["name"], "quantity": i["quantity"],
                      "unit": i["unit"], "reorder_point": i["reorder_point"], "status": stock_status(i)}
                     for i in items if stock_status(i) != "HEALTHY"),
                    key=lambda a: (a["status"] != "STOCKOUT", a["quantity"] / max(a["reorder_point"], 1)))
    return {"ingredients": len(items), "critical_stock_count": statuses["CRITICAL"],
            "stockout_count": statuses["STOCKOUT"], "inventory_alerts": alerts}


def rating_kpis(db: Any, since: str | None = None) -> dict[str, Any]:
    query = {"date": {"$gte": since}} if since else {}
    ratings = [f["rating"] for f in db.feedback.find(query, {"rating": 1})]
    return {"average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "ratings_count": len(ratings)}


def orders_between(db: Any, start: date, end: date) -> list[dict[str, Any]]:
    return list(db.orders.find({"date": {"$gte": start.isoformat(), "$lte": end.isoformat()}}))


def repeat_order_rate(orders: list[dict[str, Any]]) -> float:
    counts = Counter(o["user_id"] for o in orders if o["status"] != "cancelled")
    return pct(sum(c > 1 for c in counts.values()), len(counts))


def monthly_healthy_trend(db: Any, months: int = 6) -> list[dict[str, Any]]:
    rows = []
    first = date.today().replace(day=1)
    for offset in range(months - 1, -1, -1):
        year, month = divmod(first.year * 12 + first.month - 1 - offset, 12)
        key = f"{year:04d}-{month + 1:02d}"
        orders = list(db.orders.find({"date": {"$regex": f"^{key}"}}))
        kpis = order_kpis(orders)
        rows.append({"month": key, "orders": kpis["orders"], "healthy_meal_adoption": kpis["healthy_meal_adoption"],
                     "accepted_order_value": kpis["accepted_order_value"]})
    return rows


def last_days(days: int) -> tuple[date, date]:
    end = date.today()
    return end - timedelta(days=days - 1), end
