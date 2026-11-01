"""Seed MongoDB for ECOS. Usage: python -m backend.seed [--reset] [--history]"""

import argparse

from backend.app.core.common import today
from backend.app.core.database import ensure_indexes, get_db, init_client
from backend.app.core.seed import ensure_menus, seed, seed_demo_history

COLLECTIONS = ["users", "ingredients", "recipes", "menus", "orders", "inventory_movements",
               "feedback", "forecasts", "recommendation_events"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Drop all ECOS collections first")
    parser.add_argument("--history", action="store_true", help="Add 8 weeks of demo collected orders")
    args = parser.parse_args()

    init_client()
    db = get_db()
    if args.reset:
        for name in COLLECTIONS:
            db[name].drop()
        ensure_indexes(db)
        print("Dropped ECOS collections")
    seed(db)
    ensure_menus(db, today())
    if args.history:
        print(f"Inserted {seed_demo_history(db)} demo history orders")
    for name in COLLECTIONS:
        print(f"{name}: {db[name].count_documents({})}")
