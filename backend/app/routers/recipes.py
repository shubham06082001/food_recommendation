from typing import Any

from fastapi import APIRouter, Depends, Query

from ..core.common import serialize
from ..core.database import get_db

router = APIRouter()


@router.get("/recipes")
def list_recipes(evidence_status: str | None = Query(default=None), db: Any = Depends(get_db)) -> dict:
    query = {"evidence_status": evidence_status} if evidence_status else {}
    return {"success": True, "data": [serialize(r) for r in db.recipes.find(query).sort("name", 1)]}
