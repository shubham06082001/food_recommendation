from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from ..core.catalog import ensure_catalog
from ..core.common import current_user, eligibility
from ..core.database import get_db
from ..core.menu import menu_count, menu_items

router = APIRouter()

MealPeriod = Literal["breakfast", "snacks", "lunch", "dinner"]


@router.get("/menu")
def get_menu(
    meal_period: MealPeriod | None = None,
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=12, ge=1, le=60),
    offset: int = Query(default=0, ge=0, le=10000),
    user: dict = Depends(current_user),
    db: Any = Depends(get_db),
) -> dict:
    """The orderable menu (every catalog recipe a manager has not excluded), paged and searchable by name."""
    catalog_empty = db.recipes.count_documents({}, limit=1) == 0
    if catalog_empty:
        ensure_catalog(db)  # A fresh database fills itself from Qdrant.
    items = menu_items(db, meal_period, text=q, skip=offset, limit=limit)
    for item in items:
        item["eligible"], item["eligibility_note"] = eligibility(item, user.get("preferences", {}))
    return {"meal_period": meal_period, "query": q, "total": menu_count(db, meal_period, q), "offset": offset,
            "limit": limit, "catalog_empty": catalog_empty, "items": items}
