from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.common import current_user
from ..core.database import get_db
from ..core.recommender import recommend

router = APIRouter()


class RecommendationRequest(BaseModel):
    meal_period: Literal["breakfast", "snacks", "lunch", "dinner"] | None = None
    query: str = Field(default="", max_length=200)
    limit: int = Field(default=5, ge=1, le=20)
    exclude_dish_ids: list[str] = Field(default_factory=list, max_length=50)


@router.post("/recommendations")
def recommendations(payload: RecommendationRequest, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    """Computed live from menu, stock, profile, history and the query; never persisted."""
    return recommend(db, user, payload.query, payload.meal_period, payload.limit, payload.exclude_dish_ids)
