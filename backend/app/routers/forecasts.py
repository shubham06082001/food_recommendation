"""Demand forecast: trained Random Forest models when they beat the baseline, else same-weekday average."""

import math
from collections import defaultdict
from datetime import date as Date, timedelta
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.common import MEAL_PERIODS, now_utc, require_manager, serialize
from ..core.database import get_db
from ..core.menu import stock_map
from ml.predictor import get_predictor, reload_predictor
from ml.train import InsufficientHistory, train as train_models

router = APIRouter()

DEFAULT_PORTIONS = 10  # Planning default for dishes with no sales history.
HISTORY_DAYS = 120
HISTORY_FIELDS = {"_id": 0, "date": 1, "meal_period": 1, "user_id": 1, "items.dish_id": 1, "items.quantity": 1}


class ForecastRequest(BaseModel):
    date: Date = Field(default_factory=lambda: Date.today() + timedelta(days=1))
    meal_period: Literal["breakfast", "snacks", "lunch", "dinner"] | None = None
    buffer_percent: float = Field(default=5, ge=0, le=50)
    weeks: int = Field(default=4, ge=1, le=12)


def _menu_for(db: Any, target: str, period: str) -> list[str]:
    menu = db.menus.find_one({"date": target, "meal_period": period, "published": True})
    if menu:
        return [d for d in menu["dish_ids"] if d not in menu.get("paused_dish_ids", [])]
    return [r["dish_id"] for r in db.recipes.find({"meal_periods": period, "evidence_status": "confirmed"})]


def run(db: Any, payload: ForecastRequest) -> dict[str, Any]:
    target = payload.date
    history_dates = [(target - timedelta(weeks=w)).isoformat() for w in range(1, payload.weeks + 1)]
    periods = [payload.meal_period] if payload.meal_period else MEAL_PERIODS
    orders = list(db.orders.find({"date": {"$in": history_dates}, "status": {"$ne": "cancelled"}}))
    observed_dates = {o["date"] for o in orders}

    recipes = {r["dish_id"]: r for r in db.recipes.find({})}
    stock = stock_map(db)
    predictor = get_predictor()
    model_used = False
    dish_rows, needs = [], defaultdict(float)
    customers: dict[str, float] = {}
    for period in periods:
        period_orders = [o for o in orders if o.get("meal_period") == period]
        users_by_day = defaultdict(set)
        sold = defaultdict(int)
        for order in period_orders:
            users_by_day[order["date"]].add(order["user_id"])
            for item in order["items"]:
                sold[item["dish_id"]] += item["quantity"]
        days = len({o["date"] for o in period_orders})
        customers[period] = round(sum(len(u) for u in users_by_day.values()) / days, 1) if days else 0
        dish_ids = [d for d in _menu_for(db, target.isoformat(), period) if d in recipes]
        history = list(db.orders.find({"meal_period": period, "status": {"$ne": "cancelled"}, "date": {
            "$lt": target.isoformat(), "$gte": (target - timedelta(days=HISTORY_DAYS)).isoformat()}}, HISTORY_FIELDS))
        predicted = predictor.predict(history, period, target, dish_ids) or {"customers": None, "dishes": {}}
        if predicted["customers"] is not None:
            customers[period], model_used = round(predicted["customers"], 1), True
        for dish_id in dish_ids:
            recipe = recipes[dish_id]
            expected = predicted["dishes"].get(dish_id)
            if expected is None:
                expected = sold[dish_id] / days if days else DEFAULT_PORTIONS
            else:
                model_used = True
            prepare = math.ceil(expected * (1 + payload.buffer_percent / 100))
            for line in recipe["ingredients"]:
                needs[line["ingredient_id"]] += line["quantity"] * prepare
            dish_rows.append({"dish_id": dish_id, "name": recipe["name"], "meal_period": period,
                              "expected_orders": round(expected, 1), "recommended_preparation": prepare,
                              "projected_order_value": round(expected * recipe["price"], 2)})

    ingredients = []
    for ingredient_id, required in needs.items():
        item = stock.get(ingredient_id, {})
        on_hand = float(item.get("quantity", 0))
        ingredients.append({"ingredient_id": ingredient_id, "name": item.get("name", ingredient_id),
                            "unit": item.get("unit"), "required": round(required, 2), "on_hand": on_hand,
                            "shortfall": round(max(required - on_hand, 0), 2)})
    ingredients.sort(key=lambda i: -i["shortfall"])
    method = "random_forest" if model_used else "same_weekday_average" if observed_dates else "default_no_history"
    meta = predictor.metadata or {}
    model = {"version": meta.get("model_version"), "trained_at": meta.get("trained_at"),
             "demo_order_share": meta.get("demo_order_share"),
             **{name: {k: meta[name][k] for k in ("mae", "wape", "baseline_mae", "baseline_wape")}
                for name in predictor.models}} if model_used else None
    notes = {"random_forest": "Random Forest demand models (beat the same-weekday baseline on held-out dates); "
                              "baseline used where a dish has no history.",
             "same_weekday_average": "Average of the same weekday over recent weeks.",
             "default_no_history": f"No history for this weekday yet; using {DEFAULT_PORTIONS} portions per dish."}
    return {
        "forecast_id": f"FC-{uuid4().hex[:8].upper()}", "date": target.isoformat(), "meal_period": payload.meal_period,
        "method": method, "model": model, "history_days_used": len(observed_dates),
        "buffer_percent": payload.buffer_percent,
        "expected_customers": round(sum(customers.values())), "expected_customers_by_period": customers,
        "dishes": dish_rows, "ingredients": ingredients,
        "shortfalls": [i for i in ingredients if i["shortfall"] > 0],
        "projected_order_value": round(sum(d["projected_order_value"] for d in dish_rows), 2),
        "note": notes[method], "created_at": now_utc(),
    }


@router.post("/forecast/run")
def run_forecast(payload: ForecastRequest, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    forecast = run(db, payload)
    db.forecasts.insert_one({**forecast})
    return serialize(forecast)


@router.get("/forecast/latest")
def latest_forecast(forecast_date: Date | None = None, _: dict = Depends(require_manager),
                    db: Any = Depends(get_db)) -> dict:
    query = {"date": forecast_date.isoformat()} if forecast_date else {}
    forecast = db.forecasts.find_one(query, sort=[("created_at", -1)])
    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast has been run yet")
    return serialize(forecast)


def _model_status(metadata: dict | None, active: list[str]) -> dict:
    return {"trained": metadata is not None, "active_models": active, "metadata": metadata}


@router.get("/forecast/model")
def model_status(_: dict = Depends(require_manager)) -> dict:
    predictor = get_predictor()
    return _model_status(predictor.metadata, sorted(predictor.models))


@router.post("/forecast/model/train")
def retrain_models(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    try:
        metadata = train_models(db)
    except InsufficientHistory as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    predictor = reload_predictor()
    return _model_status(metadata, sorted(predictor.models))
