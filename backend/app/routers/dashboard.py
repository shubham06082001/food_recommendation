from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..core.analytics import (ACTIVE, inventory_kpis, last_days, monthly_healthy_trend, order_kpis, orders_between,
                              rating_kpis, repeat_order_rate)
from ..core.common import current_meal_period, current_user, now_utc, require_manager, require_self_or_manager, serialize, today
from ..core.database import get_db
from .wellness import monthly

router = APIRouter()


@router.get("/dashboard/employee/{user_id}")
def employee_dashboard(user_id: str, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    require_self_or_manager(user_id, user)
    owner = db.users.find_one({"user_id": user_id})
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")
    active = db.orders.find_one({"user_id": user_id, "status": {"$in": ACTIVE}}, sort=[("created_at", -1)])
    previous = db.orders.find_one({"user_id": user_id, "status": "collected"}, sort=[("created_at", -1)])
    scorecard = monthly(user_id, None, user, db)
    return {
        "user_id": user_id, "name": owner.get("name", user_id), "profile_complete": bool(owner.get("profile_complete")),
        "preferences": owner.get("preferences", {}), "current_meal_period": current_meal_period(datetime.now().hour),
        "active_order": serialize(active) if active else None,
        "previous_order": serialize(previous) if previous else None,
        "wellness_summary": {"month": scorecard["month"], "wellness_score": scorecard["wellness_score"],
                             "meals_tracked": scorecard["meals_tracked"],
                             "categories": scorecard["categories"], "goal_progress": scorecard["goal_progress"]},
        "as_of": now_utc().isoformat(),
    }


@router.get("/dashboard/manager")
def manager_dashboard(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    orders = list(db.orders.find({"date": today()}))
    forecast = db.forecasts.find_one({"date": today()}, sort=[("created_at", -1)])
    kpis = order_kpis(orders)
    return {
        "orders_today": kpis["orders"], **{k: kpis[k] for k in (
            "accepted_order_value", "collected_orders", "active_orders", "cancelled_orders", "top_dishes",
            "healthy_meal_adoption", "recommendation_share", "status_counts", "average_order_value")},
        "average_rating": rating_kpis(db, today())["average_rating"],
        **inventory_kpis(db),
        "expected_customers": forecast["expected_customers"] if forecast else None,
        "actual_customers": kpis["customers"],
        "forecast_method": forecast["method"] if forecast else None,
        "as_of": now_utc().isoformat(), "data_state": "connected",
    }


@router.get("/dashboard/executive")
def executive_dashboard(days: int = 30, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    days = min(max(days, 1), 365)
    start, end = last_days(days)
    orders = orders_between(db, start, end)
    kpis = order_kpis(orders)
    inventory = inventory_kpis(db)
    since = {"created_at": {"$gte": datetime.combine(start, datetime.min.time()).astimezone()}}
    replenishments = db.inventory_movements.count_documents({"type": "replenishment", **since})
    consumption = list(db.inventory_movements.aggregate([
        {"$match": {"type": "order_consumption", **since}},
        {"$group": {"_id": "$ingredient_id", "used": {"$sum": {"$abs": "$quantity"}}}},
        {"$sort": {"used": -1}}, {"$limit": 8}]))
    names = {i["ingredient_id"]: (i["name"], i["unit"]) for i in db.ingredients.find({})}
    forecast_rows = []
    for forecast in db.forecasts.find({"date": {"$gte": start.isoformat(), "$lte": date.today().isoformat()}}):
        actual = order_kpis([o for o in orders if o["date"] == forecast["date"]])["customers"]
        forecast_rows.append({"date": forecast["date"], "expected": forecast["expected_customers"], "actual": actual})
    return {
        "period_days": days, "from": start.isoformat(), "to": end.isoformat(),
        "customer": {**rating_kpis(db, start.isoformat()), "repeat_order_rate": repeat_order_rate(orders),
                     "recommendation_share": kpis["recommendation_share"],
                     "healthy_meal_adoption": kpis["healthy_meal_adoption"], "customers": kpis["customers"]},
        "operations": {"orders": kpis["orders"], "fulfilment_rate": kpis["fulfilment_rate"],
                       "average_completion_minutes": kpis["average_completion_minutes"],
                       "cancelled_orders": kpis["cancelled_orders"], "forecast_vs_actual": forecast_rows[-10:]},
        "inventory": {"critical_stock_count": inventory["critical_stock_count"],
                      "stockout_count": inventory["stockout_count"], "replenishments": replenishments,
                      "top_consumption": [{"ingredient": names.get(c["_id"], (c["_id"], ""))[0],
                                           "unit": names.get(c["_id"], ("", ""))[1], "used": round(c["used"], 1)}
                                          for c in consumption]},
        "financial": {k: kpis[k] for k in ("accepted_order_value", "collected_order_value", "average_order_value")},
        "top_dishes": kpis["top_dishes"], "monthly_trend": monthly_healthy_trend(db),
        "as_of": now_utc().isoformat(),
    }
