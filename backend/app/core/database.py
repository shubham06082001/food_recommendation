from typing import Any

from pymongo import MongoClient

from .config import settings

_client: MongoClient | None = None


def init_client() -> None:
    global _client  # pylint: disable=global-statement
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000, tz_aware=True)
        _client.admin.command("ping")
        ensure_indexes(_client[settings.mongodb_db])


def ensure_indexes(db: Any) -> None:
    db.users.create_index("user_id", unique=True)
    db.ingredients.create_index("ingredient_id", unique=True)
    db.recipes.create_index("dish_id", unique=True)
    db.menus.create_index([("date", 1), ("meal_period", 1)], unique=True)
    db.orders.create_index("order_id", unique=True)
    db.orders.create_index([("user_id", 1), ("date", -1)])
    db.inventory_movements.create_index([("ingredient_id", 1), ("created_at", -1)])
    db.orders.create_index([("status", 1), ("date", -1)])
    db.feedback.create_index("order_id", unique=True)
    db.feedback.create_index("user_id")
    db.sessions.create_index("token", unique=True)
    db.sessions.create_index("expires_at", expireAfterSeconds=0)
    db.inventory_movements.create_index("order_id")
    db.forecasts.create_index([("date", 1), ("created_at", -1)])


def get_db() -> Any:
    if _client is None:
        raise RuntimeError("mongodb client not initialised")
    return _client[settings.mongodb_db]
