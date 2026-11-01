"""Monthly food-choice scorecard computed from an employee's collected orders."""

from collections import Counter
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.common import HEALTHY_TAGS, current_user, pct, require_self_or_manager
from ..core.database import get_db

router = APIRouter()

DISCLAIMER = "This scorecard summarises recorded food choices and is not a medical or clinical assessment."
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
BASE_SCORE = 20  # Every employee starts each month at 20; ordered portions add points up to 100.


def wellness_score(db: Any, user_id: str, month: str) -> int:
    orders = db.orders.find({"user_id": user_id, "status": {"$ne": "cancelled"}, "date": {"$regex": f"^{month}"}})
    points = sum((10 if set(HEALTHY_TAGS) & set(i.get("nutrition_tags", [])) else 5) * i["quantity"]
                 for o in orders for i in o["items"])
    return min(100, BASE_SCORE + points)


def shift_month(month: str, offset: int) -> str:
    year, mon = map(int, month.split("-"))
    index = year * 12 + (mon - 1) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_stats(db: Any, user_id: str, month: str) -> dict[str, Any]:
    orders = list(db.orders.find({"user_id": user_id, "status": "collected", "date": {"$regex": f"^{month}"}}))
    portions = Counter()
    periods = Counter()
    dishes = Counter()
    total = recommended = 0
    for order in orders:
        periods[order.get("meal_period", "other")] += 1
        for item in order["items"]:
            total += item["quantity"]
            dishes[item["name"]] += item["quantity"]
            recommended += item["quantity"] if item.get("recommended") else 0
            for tag in item.get("nutrition_tags", []):
                portions[tag] += item["quantity"]
    return {"orders": orders, "total": total, "portions": portions, "periods": periods,
            "dishes": dishes, "recommended": recommended}


@router.get("/wellness/{user_id}/monthly")
def monthly(user_id: str, month: str | None = Query(default=None, pattern=MONTH_PATTERN),
            user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    require_self_or_manager(user_id, user)
    owner = db.users.find_one({"user_id": user_id})
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")
    month = month or date.today().strftime("%Y-%m")
    current, previous = month_stats(db, user_id, month), month_stats(db, user_id, shift_month(month, -1))

    categories = {}
    for tag in HEALTHY_TAGS:
        share = pct(current["portions"][tag], current["total"])
        prior = pct(previous["portions"][tag], previous["total"]) if previous["total"] else None
        categories[tag] = {"meal_count": current["portions"][tag], "percentage": share,
                           "previous_month_percentage": prior,
                           "change_percentage_points": round(share - prior, 1) if prior is not None else None}

    goals = owner.get("preferences", {}).get("wellness_goals", [])
    goal_progress = [{"goal": g, "matching_meals": current["portions"][g], "eligible_meals": current["total"],
                      "match_rate": pct(current["portions"][g], current["total"])} for g in goals]

    pending = db.orders.count_documents({"user_id": user_id, "date": {"$regex": f"^{month}"},
                                         "status": {"$in": ["confirmed", "preparing", "ready"]}})
    return {
        "user_id": user_id, "month": month, "wellness_score": wellness_score(db, user_id, month),
        "meals_tracked": current["total"], "orders_collected": len(current["orders"]),
        "orders_pending_collection": pending, "categories": categories, "goal_progress": goal_progress,
        "recommendation_engagement": {"recommended_meals_ordered": current["recommended"],
                                      "share_of_meals_recommended": pct(current["recommended"], current["total"])},
        "meal_period_coverage": dict(current["periods"]),
        "top_dishes": [{"name": n, "portions": q} for n, q in current["dishes"].most_common(5)],
        "disclaimer": DISCLAIMER,
    }


@router.get("/wellness/{user_id}/trend")
def trend(user_id: str, months: int = Query(default=6, ge=1, le=24),
          user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    require_self_or_manager(user_id, user)
    this_month = date.today().strftime("%Y-%m")
    rows = []
    for offset in range(months - 1, -1, -1):
        month = shift_month(this_month, -offset)
        stats = month_stats(db, user_id, month)
        rows.append({"month": month, "meals_tracked": stats["total"],
                     **{f"{tag}_percentage": pct(stats["portions"][tag], stats["total"]) for tag in HEALTHY_TAGS}})
    return {"user_id": user_id, "trend": rows, "disclaimer": DISCLAIMER}
