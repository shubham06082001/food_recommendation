import threading
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.collation import Collation

from ..core import catalog
from ..core.common import require_manager
from ..core.database import get_db
from ..core.menu import menu_filter

router = APIRouter()

MealPeriod = Literal["breakfast", "snacks", "lunch", "dinner"]
COLUMNS = {"_id": 0, "dish_id": 1, "name": 1, "diet": 1, "price": 1, "price_source": 1, "meal_periods": 1, "on_menu": 1,
           "declared_allergens": 1, "source": 1, "catalog_code": 1, "image_url": 1, "ingredients": 1}


class RecipeUpdate(BaseModel):
    dish_id: str
    on_menu: bool | None = None
    price: float | None = Field(default=None, gt=0, le=5000)
    meal_periods: list[MealPeriod] | None = Field(default=None, min_length=1, max_length=4)


class RecipeUpdates(BaseModel):
    updates: list[RecipeUpdate] = Field(min_length=1, max_length=200)


class BulkMenu(BaseModel):
    on_menu: bool
    q: str = Field(default="", max_length=80)
    meal_period: MealPeriod | None = None


def _row(recipe: dict[str, Any]) -> dict[str, Any]:
    lines = recipe.pop("ingredients", [])
    return {**recipe, "on_menu": recipe.get("on_menu", True), "stock_tracked": bool(lines)}


@router.get("/recipes")
def list_recipes(
    q: str = Query(default="", max_length=80), meal_period: MealPeriod | None = None, on_menu: bool | None = None,
    limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0, le=10000),
    _: dict = Depends(require_manager), db: Any = Depends(get_db),
) -> dict:
    """Manager view of the whole recipe catalog, including recipes excluded from the menu."""
    query = menu_filter(meal_period, q)
    if on_menu is False:
        query["on_menu"] = False
    elif on_menu is None:
        query.pop("on_menu")
    rows = db.recipes.find(query, COLUMNS).collation(Collation(locale="en", strength=2)).sort("name", 1).skip(offset).limit(limit)
    return {"success": True, "total": db.recipes.count_documents(query), "data": [_row(r) for r in rows]}


@router.patch("/recipes")
def update_recipes(payload: RecipeUpdates, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    """Add or remove dishes from the menu, change their price, or change the meal periods they are served in."""
    missing, updated = [], 0
    for update in payload.updates:
        changes = update.model_dump(exclude_none=True, exclude={"dish_id"})
        if not changes:
            continue
        if "price" in changes:
            changes["price_source"] = "manager"
        result = db.recipes.update_one({"dish_id": update.dish_id}, {"$set": changes})
        updated += result.modified_count
        if not result.matched_count:
            missing.append(update.dish_id)
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown dishes: {', '.join(missing[:10])}")
    return {"success": True, "updated": updated}


@router.post("/recipes/bulk-menu")
def bulk_menu(payload: BulkMenu, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    """Include or exclude every recipe matching a search / meal period in one step."""
    query = menu_filter(payload.meal_period, payload.q)
    query.pop("on_menu")
    result = db.recipes.update_many(query, {"$set": {"on_menu": payload.on_menu}})
    return {"success": True, "matched": result.matched_count, "updated": result.modified_count}


@router.get("/catalog/status")
def catalog_status(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    return catalog.status(db)


@router.post("/catalog/sync", status_code=202)
def sync_catalog(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    """Re-read the Qdrant catalog in the background; manager choices (menu, price, periods) are preserved."""
    if not catalog.status(db)["running"]:
        threading.Thread(target=catalog.sync_catalog, args=(db,), daemon=True, name="catalog-sync").start()
    return {**catalog.status(db), "running": True}
