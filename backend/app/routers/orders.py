import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..core.common import (ORDER_STATUSES, current_meal_period, current_user, now_utc, record_movement,
                           require_manager, require_self_or_manager, serialize, today)
from ..core.database import get_db
from ..core.menu import menu_items

router = APIRouter()

# Allowed forward transitions; cancellation is possible until the order is ready.
TRANSITIONS = {
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"collected"},
    "collected": set(),
    "cancelled": set(),
}


class OrderLine(BaseModel):
    dish_id: str
    quantity: int = Field(ge=1, le=10)


class OrderRequest(BaseModel):
    items: list[OrderLine] = Field(min_length=1, max_length=15)
    recommended_dish_ids: list[str] = Field(default_factory=list, max_length=15)


class StatusRequest(BaseModel):
    status: Literal["confirmed", "preparing", "ready", "collected", "cancelled"]


def _deduct(db: Any, needs: dict[str, float]) -> list[tuple[str, float]]:
    """Atomically decrement each ingredient only if enough stock remains; roll back on failure."""
    done: list[tuple[str, float]] = []
    for ingredient_id, amount in needs.items():
        result = db.ingredients.update_one(
            {"ingredient_id": ingredient_id, "quantity": {"$gte": amount}},
            {"$inc": {"quantity": -amount}, "$set": {"updated_at": now_utc()}})
        if not result.modified_count:
            for rolled_id, rolled_amount in done:
                db.ingredients.update_one({"ingredient_id": rolled_id}, {"$inc": {"quantity": rolled_amount}})
            name = (db.ingredients.find_one({"ingredient_id": ingredient_id}) or {}).get("name", ingredient_id)
            raise HTTPException(status_code=409, detail=f"Not enough {name} in stock for this order")
        done.append((ingredient_id, amount))
    return done


@router.post("/orders", status_code=201)
def create_order(payload: OrderRequest, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    if user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Only employees can place orders")
    period_now = current_meal_period(datetime.now().hour)
    menu: dict[str, dict[str, Any]] = {}
    # A dish served in several periods is attributed to the current one when possible.
    for item in sorted(menu_items(db), key=lambda i: i["meal_period"] != period_now):
        menu.setdefault(item["dish_id"], item)
    quantities: dict[str, int] = defaultdict(int)
    for line in payload.items:
        quantities[line.dish_id] += line.quantity

    recommended = set(payload.recommended_dish_ids)

    lines, needs = [], defaultdict(float)
    for dish_id, quantity in quantities.items():
        dish = menu.get(dish_id)
        if not dish:
            raise HTTPException(status_code=400, detail=f"{dish_id} is not on today's menu")
        if not dish["available"]:
            raise HTTPException(status_code=409, detail=f"{dish['name']} is unavailable: {dish['unavailable_reason']}")
        for ingredient in dish["ingredients"]:
            needs[ingredient["ingredient_id"]] += float(ingredient["quantity"]) * quantity
        lines.append({"dish_id": dish_id, "name": dish["name"], "quantity": quantity,
                      "unit_price": dish["price"], "line_total": dish["price"] * quantity,
                      "meal_period": dish["meal_period"], "nutrition_tags": dish.get("nutrition_tags", []),
                      "recommended": dish_id in recommended})

    order_id = f"ORD-{uuid4().hex[:10].upper()}"
    _deduct(db, needs)
    for ingredient_id, amount in needs.items():
        record_movement(db, ingredient_id, "order_consumption", -amount, user["user_id"], order_id=order_id)

    order = {
        "order_id": order_id, "pickup_reference": f"{random.choice('ABCDEFGH')}{random.randint(100, 999)}",
        "user_id": user["user_id"], "items": lines, "total": sum(l["line_total"] for l in lines),
        "meal_period": lines[0]["meal_period"], "status": "confirmed", "payment": "demo_paid",
        "date": today(), "created_at": now_utc(),
    }
    db.orders.insert_one(order)
    return {"success": True, "order_id": order_id, "pickup_reference": order["pickup_reference"],
            "total": order["total"], "status": "confirmed"}


@router.get("/orders")
def list_orders(
    user_id: str | None = None, status: str | None = None,
    order_date: str | None = Query(default=None, alias="date"), limit: int = Query(default=100, le=500),
    user: dict = Depends(current_user), db: Any = Depends(get_db),
) -> dict:
    if user.get("role") != "manager":
        user_id = user["user_id"]
    query: dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        if status not in ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Unknown status")
        query["status"] = status
    if order_date:
        query["date"] = order_date
    orders = db.orders.find(query).sort("created_at", -1).limit(limit)
    rated = {f["order_id"]: f["rating"] for f in db.feedback.find({"user_id": user_id} if user_id else {})}
    return {"success": True, "data": [{**serialize(o), "rating": rated.get(o["order_id"])} for o in orders]}


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    order = db.orders.find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    require_self_or_manager(order["user_id"], user)
    return serialize(order)


@router.patch("/orders/{order_id}/status")
def update_status(order_id: str, payload: StatusRequest, manager: dict = Depends(require_manager),
                  db: Any = Depends(get_db)) -> dict:
    order = db.orders.find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.status not in TRANSITIONS[order["status"]]:
        raise HTTPException(status_code=400, detail=f"Cannot move order from {order['status']} to {payload.status}")
    changes: dict[str, Any] = {"status": payload.status, f"{payload.status}_at": now_utc()}
    result = db.orders.update_one({"order_id": order_id, "status": order["status"]}, {"$set": changes})
    if not result.modified_count:
        raise HTTPException(status_code=409, detail="Order was updated by someone else; refresh and retry")
    if payload.status == "cancelled":
        for movement in db.inventory_movements.find({"order_id": order_id, "type": "order_consumption"}):
            restored = -movement["quantity"]
            db.ingredients.update_one({"ingredient_id": movement["ingredient_id"]}, {"$inc": {"quantity": restored}})
            record_movement(db, movement["ingredient_id"], "order_cancelled", restored, manager["user_id"],
                            order_id=order_id)
    return {"success": True, "order_id": order_id, "status": payload.status}
