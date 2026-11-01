from datetime import date as Date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..core.common import eligibility, now_utc, require_manager
from ..core.database import get_db
from ..core.menu import menu_items

router = APIRouter()

MealPeriod = Literal["breakfast", "snacks", "lunch", "dinner"]


class MenuRequest(BaseModel):
    date: Date
    meal_period: MealPeriod
    dish_ids: list[str] = Field(min_length=1)


class MenuItemUpdate(BaseModel):
    paused: bool


@router.get("/menu")
def get_menu(
    meal_period: MealPeriod | None = None,
    user_id: str | None = None,
    menu_date: Date | None = Query(default=None, alias="date"),
    db: Any = Depends(get_db),
) -> dict:
    items = menu_items(db, meal_period, menu_date.isoformat() if menu_date else None)
    if user_id:
        user = db.users.find_one({"user_id": user_id}) or {}
        for item in items:
            item["eligible"], item["eligibility_note"] = eligibility(item, user.get("preferences", {}))
    return {"meal_period": meal_period, "date": (menu_date or Date.today()).isoformat(), "items": items}


@router.post("/menu")
def publish_menu(payload: MenuRequest, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    dish_ids = list(dict.fromkeys(payload.dish_ids))
    recipes = list(db.recipes.find({"dish_id": {"$in": dish_ids}}, {"dish_id": 1, "evidence_status": 1}))
    missing = set(dish_ids) - {r["dish_id"] for r in recipes}
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown dishes: {', '.join(sorted(missing))}")
    unconfirmed = [r["dish_id"] for r in recipes if r.get("evidence_status") != "confirmed"]
    if unconfirmed:
        raise HTTPException(status_code=400, detail="Only confirmed recipes can be published")
    menu_date = payload.date.isoformat()
    menu = {"menu_id": f"MENU-{menu_date}-{payload.meal_period}", "date": menu_date,
            "meal_period": payload.meal_period, "dish_ids": dish_ids, "published": True, "updated_at": now_utc()}
    db.menus.update_one({"date": menu_date, "meal_period": payload.meal_period},
                        {"$set": menu, "$setOnInsert": {"paused_dish_ids": []}}, upsert=True)
    return {"success": True, "menu_id": menu["menu_id"], "dish_count": len(dish_ids)}


@router.patch("/menu/{menu_id}/items/{dish_id}")
def pause_menu_item(
    menu_id: str, dish_id: str, payload: MenuItemUpdate,
    _: dict = Depends(require_manager), db: Any = Depends(get_db),
) -> dict:
    operator = "$addToSet" if payload.paused else "$pull"
    result = db.menus.update_one({"menu_id": menu_id, "dish_ids": dish_id},
                                 {operator: {"paused_dish_ids": dish_id}, "$set": {"updated_at": now_utc()}})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Dish is not on this menu")
    return {"success": True, "menu_id": menu_id, "dish_id": dish_id, "paused": payload.paused}
