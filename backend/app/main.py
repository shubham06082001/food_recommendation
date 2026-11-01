from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .core.config import settings
from .core.database import get_db, init_client
from .core.seed import seed
from .routers import (
    copilot, dashboard, feedback, forecasts, health, inventory, menus,
    orders, recipes, recommendations, uploads, users, wellness,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_client()
    if settings.seed_on_startup:
        seed(get_db())
    yield


app = FastAPI(title="ECOS backend", version="1.0.0", lifespan=lifespan)


@app.exception_handler(PyMongoError)
async def database_error(_: Request, error: PyMongoError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": f"Database unavailable: {type(error).__name__}"})


for module in (
    health, users, recipes, menus, recommendations, orders, feedback,
    inventory, uploads, forecasts, wellness, dashboard, copilot,
):
    app.include_router(module.router, prefix="/api/v1", tags=[module.__name__.rsplit(".", 1)[-1]])
