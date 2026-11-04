import threading
from typing import Any

from pymongo import MongoClient

from .config import settings

_client: MongoClient | None = None
_lock = threading.Lock()


def init_client() -> None:
    """Connect once; a failed attempt leaves no client behind so the next request retries."""
    global _client  # pylint: disable=global-statement
    with _lock:
        if _client is not None:
            return
        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000, tz_aware=True)
        try:
            client.admin.command("ping")
            ensure_indexes(client[settings.mongodb_db])
        except Exception:
            client.close()
            raise
        _client = client


def ensure_indexes(db: Any) -> None:
    """Idempotent, so a brand-new database is ready to use after the first connection."""
    db.users.create_index("user_id", unique=True)
    db.ingredients.create_index("ingredient_id", unique=True)
    db.recipes.create_index("dish_id", unique=True)
    db.recipes.create_index([("on_menu", 1), ("meal_periods", 1)])
    db.recipes.create_index("catalog_code")
    db.orders.create_index("order_id", unique=True)
    db.orders.create_index([("user_id", 1), ("date", -1)])
    db.orders.create_index([("status", 1), ("date", -1)])
    db.orders.create_index([("user_id", 1), ("request_id", 1)], unique=True,
                           partialFilterExpression={"request_id": {"$type": "string"}})
    db.inventory_movements.create_index([("ingredient_id", 1), ("created_at", -1)])
    db.inventory_movements.create_index("order_id")
    db.feedback.create_index("order_id", unique=True)
    db.feedback.create_index("user_id")
    for name, info in db.sessions.index_information().items():  # Sessions used to be keyed by the raw token.
        if info["key"] == [("token", 1)]:
            db.sessions.drop_index(name)
    db.sessions.create_index("token_hash", unique=True)
    db.sessions.create_index("expires_at", expireAfterSeconds=0)
    db.forecasts.create_index([("date", 1), ("created_at", -1)])


def get_db() -> Any:
    if _client is None:
        init_client()
    return _client[settings.mongodb_db]
