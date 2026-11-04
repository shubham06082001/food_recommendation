"""Operate the ECOS database. Usage: python -m backend.seed [--reset] [--demo] [--history] [--sync]

A new, empty database needs none of this: the API creates indexes, the manager account (from
ECOS_MANAGER_PASSWORD) and the menu (synced from Qdrant) on its own. These flags are for maintenance.
"""

import argparse

from backend.app.core import catalog
from backend.app.core.database import ensure_indexes, get_db
from backend.app.core.seed import bootstrap, seed_demo, seed_demo_history

COLLECTIONS = ["users", "ingredients", "recipes", "orders", "inventory_movements", "feedback", "forecasts",
               "sessions", "meta"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Drop all ECOS collections first")
    parser.add_argument("--demo", action="store_true", help="Add demo ingredients and recipes with stock lines")
    parser.add_argument("--history", action="store_true", help="Add 8 weeks of demo collected orders (implies --demo)")
    parser.add_argument("--sync", action="store_true", help="Sync recipes from the Qdrant catalog now")
    args = parser.parse_args()

    db = get_db()
    if args.reset:
        for name in COLLECTIONS:
            db[name].drop()
        ensure_indexes(db)
        print("Dropped ECOS collections")
    bootstrap(db)
    if args.demo or args.history:
        seed_demo(db)
    if args.history:
        print(f"Inserted {seed_demo_history(db)} demo history orders")
    if args.sync or args.reset:
        print("Catalog sync:", catalog.sync_catalog(db))
    for name in COLLECTIONS:
        print(f"{name}: {db[name].count_documents({})}")
