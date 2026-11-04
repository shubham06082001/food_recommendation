import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .core.catalog import ensure_catalog
from .core.config import settings
from .core.database import get_db
from .core.enrich import enrich_in_background
from .core.seed import bootstrap, seed_demo
from .core.vectors import start_warm_up
from .routers import (
    copilot, dashboard, feedback, forecasts, health, inventory, inventory_consumption, menus,
    orders, recipes, recommendations, uploads, users, wellness,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for noisy in ("httpx", "httpcore", "sentence_transformers", "qdrant_client"):  # One INFO line per outgoing call otherwise.
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("ecos")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start-up never depends on existing data: an empty database gets its indexes, manager and menu on its own."""
    start_warm_up()
    try:
        db = get_db()  # Connects and creates indexes.
        bootstrap(db)
        if settings.seed_demo:
            seed_demo(db)
        ensure_catalog(db)
        enrich_in_background(db)
    except PyMongoError as error:  # The API still starts; /health reports 503 and requests retry the connection.
        logger.error("Started without a database connection: %s", error)
    yield


app = FastAPI(title="ECOS backend", version="1.1.0", lifespan=lifespan)


@app.exception_handler(PyMongoError)
async def database_error(_: Request, error: PyMongoError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": f"Database unavailable: {type(error).__name__}"})


for module in (
    health, users, recipes, menus, recommendations, orders, feedback,
    inventory, inventory_consumption, uploads, forecasts, wellness, dashboard, copilot,
):
    app.include_router(module.router, prefix="/api/v1", tags=[module.__name__.rsplit(".", 1)[-1]])
