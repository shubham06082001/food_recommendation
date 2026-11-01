from typing import Any

from fastapi import APIRouter, Depends, Query

from ..core.common import require_manager, today
from ..core.database import get_db

router = APIRouter()


@router.get("/inventory/consumption-by-order")
def consumption_by_order(date: str | None = Query(default=None), limit: int = Query(default=200, le=1000),
                         _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    """Per-order ingredient consumption for a given service day (manager view).

    Aggregates inventory_movements rows of type "order_consumption" into a per-order table so managers
    can see which ingredients and quantities were used to serve orders on a specific date.
    """
    day = date or today()
    pipeline = [
        {"$match": {"type": "order_consumption", "date": day}},
        {"$group": {
            "_id": {"order_id": "$order_id", "ingredient_id": "$ingredient_id"},
            "used": {"$sum": "$quantity"},
        }},
        {"$sort": {"_id.order_id": 1}},
        {"$limit": limit},
    ]
    rows = list(db.inventory_movements.aggregate(pipeline))
    ingredients = {i["ingredient_id"]: (i.get("name"), i.get("unit")) for i in db.ingredients.find({})}
    data: list[dict[str, Any]] = []
    for row in rows:
        order_id = row["_id"]["order_id"]
        ingredient_id = row["_id"]["ingredient_id"]
        name, unit = ingredients.get(ingredient_id, (ingredient_id, ""))
        data.append({
            "order_id": order_id,
            "ingredient_id": ingredient_id,
            "ingredient_name": name,
            "used_quantity": abs(row["used"]),
            "unit": unit,
        })
    return {"success": True, "date": day, "data": data}
