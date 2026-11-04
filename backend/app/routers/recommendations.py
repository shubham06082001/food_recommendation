from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.common import current_user
from ..core.database import get_db
from ..core.recommender import meal_plan, recommend

router = APIRouter()


class RecommendationRequest(BaseModel):
    meal_period: Literal["breakfast", "snacks", "lunch", "dinner"] | None = None
    query: str = Field(default="", max_length=200)
    limit: int = Field(default=5, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=2000, description="Skip this many ranked results (next page)")
    exclude_dish_ids: list[str] = Field(default_factory=list, max_length=50)


@router.post("/recommendations")
def recommendations(payload: RecommendationRequest, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    """Computed live from menu, stock, profile, history and the query; never persisted."""
    return recommend(db, user, payload.query, payload.meal_period, payload.limit, payload.exclude_dish_ids,
                     offset=payload.offset)


class MealPlanRequest(BaseModel):
    query: str = Field(default="", max_length=200)


@router.post("/recommendations/meal-plan")
def day_plan(payload: MealPlanRequest, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    return meal_plan(db, user, payload.query)
