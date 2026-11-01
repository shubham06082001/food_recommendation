from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ..core.common import now_utc, record_movement, require_manager, serialize, stock_status, today
from ..core.database import get_db
from ..core.menu import menu_items, stock_map
from ..core.semantic import semantic_scores

router = APIRouter()


class IngredientRequest(BaseModel):
    ingredient_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=80)
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=12)
    reorder_point: float = Field(ge=0)
    category: str = Field(default="", max_length=60)


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, max_length=60)
    reorder_point: float | None = Field(default=None, ge=0)
    quantity: float | None = Field(default=None, ge=0)
    note: str = Field(default="Manual stock adjustment", max_length=200)


class ReplenishmentRequest(BaseModel):
    quantity: float = Field(gt=0)
    note: str = Field(default="Manual replenishment", max_length=200)


def with_status(item: dict[str, Any]) -> dict[str, Any]:
    item = serialize(item)
    return {**item, "status": stock_status(item)}


def find_ingredient(db: Any, ingredient_id: str) -> dict[str, Any]:
    item = db.ingredients.find_one({"ingredient_id": ingredient_id})
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return item


@router.get("/inventory")
def list_inventory(status: str | None = Query(default=None), _: dict = Depends(require_manager),
                   db: Any = Depends(get_db)) -> dict:
    items = [with_status(i) for i in db.ingredients.find({}).sort("name", 1)]
    if status:
        items = [i for i in items if i["status"] == status.upper()]
    return {"success": True, "data": items}


@router.post("/inventory", status_code=201)
def create_ingredient(payload: IngredientRequest, manager: dict = Depends(require_manager),
                      db: Any = Depends(get_db)) -> dict:
    record = {**payload.model_dump(), "ingredient_id": payload.ingredient_id.upper(), "updated_at": now_utc()}
    try:
        db.ingredients.insert_one(record)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Ingredient already exists") from error
    record_movement(db, record["ingredient_id"], "opening_stock", record["quantity"], manager["user_id"])
    return {"success": True, "data": with_status(record)}


@router.patch("/inventory/{ingredient_id}")
def update_ingredient(ingredient_id: str, payload: IngredientUpdate, manager: dict = Depends(require_manager),
                      db: Any = Depends(get_db)) -> dict:
    changes = payload.model_dump(exclude_none=True, exclude={"note"})
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")
    previous = db.ingredients.find_one_and_update(
        {"ingredient_id": ingredient_id}, {"$set": {**changes, "updated_at": now_utc()}})
    if not previous:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    delta = changes.get("quantity", previous["quantity"]) - float(previous["quantity"])
    if delta:
        record_movement(db, ingredient_id, "manual_adjustment", delta, manager["user_id"], note=payload.note)
    return {"success": True, "previous_quantity": previous["quantity"],
            "data": with_status(db.ingredients.find_one({"ingredient_id": ingredient_id}))}


@router.get("/inventory/alerts")
def inventory_alerts(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    alerts = [i for i in (with_status(x) for x in db.ingredients.find({})) if i["status"] != "HEALTHY"]
    alerts.sort(key=lambda i: (i["status"] != "STOCKOUT", i["quantity"] / max(i["reorder_point"], 1)))
    for alert in alerts:
        alert["affected_dishes"] = db.recipes.count_documents({"ingredients.ingredient_id": alert["ingredient_id"]})
        alert["suggested_replenishment"] = round(max(alert["reorder_point"] * 2 - alert["quantity"], 0), 2)
    return {"success": True, "data": alerts}


@router.post("/inventory/{ingredient_id}/replenish")
def replenish(ingredient_id: str, payload: ReplenishmentRequest, manager: dict = Depends(require_manager),
              db: Any = Depends(get_db)) -> dict:
    previous = float(find_ingredient(db, ingredient_id).get("quantity", 0))
    updated = db.ingredients.find_one_and_update(
        {"ingredient_id": ingredient_id},
        {"$inc": {"quantity": payload.quantity}, "$set": {"updated_at": now_utc()}},
        return_document=ReturnDocument.AFTER)
    record_movement(db, ingredient_id, "replenishment", payload.quantity, manager["user_id"], note=payload.note)
    return {"success": True, "ingredient_id": ingredient_id, "previous_quantity": previous,
            "added_quantity": payload.quantity, "new_quantity": updated["quantity"],
            "unit": updated.get("unit"), "status": stock_status(updated)}


@router.get("/inventory/{ingredient_id}/affected-dishes")
def affected_dishes(ingredient_id: str, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    item = find_ingredient(db, ingredient_id)
    dishes = []
    for recipe in db.recipes.find({"ingredients.ingredient_id": ingredient_id}):
        per_portion = next(line["quantity"] for line in recipe["ingredients"] if line["ingredient_id"] == ingredient_id)
        dishes.append({"dish_id": recipe["dish_id"], "name": recipe["name"], "quantity_per_portion": per_portion,
                       "portions_possible": int(float(item["quantity"]) // per_portion) if per_portion else 0})
    return {"success": True, "ingredient": with_status(item), "data": dishes}


@router.get("/inventory/{ingredient_id}/movements")
def inventory_movements(ingredient_id: str, limit: int = Query(default=50, le=500),
                        _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    rows = db.inventory_movements.find({"ingredient_id": ingredient_id}).sort("created_at", -1).limit(limit)
    return {"success": True, "data": [serialize(r) for r in rows]}


def daily_demand(db: Any) -> tuple[dict[str, float], str]:
    """Expected portions per dish today: today's forecast if run, else the 14-day daily average."""
    forecast = db.forecasts.find_one({"date": today()}, sort=[("created_at", -1)])
    if forecast:
        demand: dict[str, float] = defaultdict(float)
        for dish in forecast["dishes"]:
            demand[dish["dish_id"]] += dish["expected_orders"]
        return demand, "today's forecast"
    start = (date.today() - timedelta(days=14)).isoformat()
    orders = list(db.orders.find({"date": {"$gte": start, "$lt": today()}, "status": {"$ne": "cancelled"}}))
    days = len({o["date"] for o in orders}) or 1
    sold: dict[str, float] = defaultdict(float)
    for order in orders:
        for item in order["items"]:
            sold[item["dish_id"]] += item["quantity"]
    return {d: round(q / days, 1) for d, q in sold.items()}, "14-day daily average"


def _swaps(dish: dict[str, Any], options: list[dict[str, Any]]) -> list[str]:
    """Up to two in-stock dishes of the same diet, ranked by Qdrant similarity when available."""
    options = [o for o in options if o["diet"] == dish.get("diet") and o["dish_id"] != dish["dish_id"]]
    scores = semantic_scores(dish["name"], [o["catalog_code"] for o in options if o.get("catalog_code")])
    options.sort(key=lambda o: (-scores.get(o.get("catalog_code"), 0.0), -o["maximum_portions"]))
    return [o["name"] for o in options[:2]]


@router.get("/inventory/risk")
def stock_risk(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    """Today's menu risk: stockouts, over-demand (lost revenue), low-stock dishes and slow movers (waste)."""
    demand, basis = daily_demand(db)
    stock = stock_map(db)
    dishes = {i["dish_id"]: i for i in menu_items(db)}.values()
    available = [d for d in dishes if d["available"]]
    average = sum(demand.get(d["dish_id"], 0) for d in dishes) / max(len(dishes), 1)
    at_risk, slow = [], []
    for dish in dishes:
        if not dish.get("ingredients"):
            continue
        expected = demand.get(dish["dish_id"], 0.0)
        portions = dish["maximum_portions"]
        limiting = min(dish["ingredients"], key=lambda l: float(stock.get(l["ingredient_id"], {}).get("quantity", 0))
                       / max(float(l["quantity"]), 1e-9))
        item = stock.get(limiting["ingredient_id"], {})
        low = stock_status(item) != "HEALTHY" if item else True
        shortfall = max(expected - portions, 0.0)
        if portions <= 0 or shortfall > 0 or low:
            at_risk.append({
                "dish_id": dish["dish_id"], "name": dish["name"], "meal_period": dish["meal_period"],
                "risk": "STOCKOUT" if portions <= 0 else "OVER_DEMAND" if shortfall > 0 else "LOW_STOCK",
                "limiting_ingredient": item.get("name", limiting["ingredient_id"]), "portions_possible": portions,
                "expected_demand": expected, "lost_portions": round(shortfall, 1),
                "revenue_at_risk": round(shortfall * dish["price"], 2), "swap_suggestions": _swaps(dish, available),
            })
        elif average and expected <= 0.25 * average:
            slow.append({"dish_id": dish["dish_id"], "name": dish["name"], "meal_period": dish["meal_period"],
                         "expected_demand": expected, "note": "Slow mover: prepare to order to limit waste"})
    at_risk.sort(key=lambda r: (-r["revenue_at_risk"], r["portions_possible"]))
    return {"demand_basis": basis, "revenue_at_risk": round(sum(r["revenue_at_risk"] for r in at_risk), 2),
            "dishes_at_risk": at_risk, "slow_movers": slow, "as_of": now_utc().isoformat()}
