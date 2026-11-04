from typing import Any

from fastapi import APIRouter, Depends

from ..core.database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Any = Depends(get_db)) -> dict:
    """Liveness plus a database round trip; a database failure surfaces as 503 via the shared handler."""
    db.command("ping")
    return {"status": "healthy", "database": "connected", "recipes": db.recipes.estimated_document_count()}
