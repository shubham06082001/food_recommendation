from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.common import current_user, now_utc
from ..core.database import get_db

router = APIRouter()


class FeedbackRequest(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    reason: Literal["taste", "portion", "quality", "waiting_time", "other"] = "other"
    comment: str = Field(default="", max_length=500)


@router.post("/feedback")
def submit_feedback(payload: FeedbackRequest, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    order = db.orders.find_one({"order_id": payload.order_id, "user_id": user["user_id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled orders cannot be rated")
    db.feedback.update_one(
        {"order_id": payload.order_id},
        {"$set": {**payload.model_dump(), "user_id": user["user_id"], "date": order["date"],
                  "dish_ids": [i["dish_id"] for i in order["items"]], "created_at": now_utc()}},
        upsert=True)
    return {"success": True}
