from typing import Any

from fastapi import APIRouter, Depends

from ..core.database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Any = Depends(get_db)) -> dict:
    db.command("ping")
    return {"status": "healthy", "database": "connected"}
