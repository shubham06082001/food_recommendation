"""Train ECOS demand models from MongoDB order history.

Run: .venv/bin/python -m ml.train        (artifacts go to $ECOS_ML_ARTIFACTS or ml/artifacts)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.features import CUSTOMER_FEATURES, DISH_FEATURES, add_features, customer_table, dish_table, order_lines

ARTIFACT_DIR = Path(os.getenv("ECOS_ML_ARTIFACTS", Path(__file__).parent / "artifacts"))
MODEL_VERSION = "ecos_demand_rf_v1"
MIN_ROWS = {"customer_demand": 12, "dish_demand": 20}


class InsufficientHistory(ValueError):
    """Not enough order history to train and evaluate a model."""


def wape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    total = float(np.abs(actual).sum())
    return round(float(np.abs(actual - predicted).sum()) / total * 100, 2) if total else None


def pipeline(categorical: list[str]) -> Pipeline:
    encoder = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), categorical)],
                                remainder="passthrough")
    model = RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=2, random_state=42, n_jobs=-1)
    return Pipeline([("prep", encoder), ("model", model)])


def fit_and_evaluate(name: str, table: pd.DataFrame, features: list[str],
                     categorical: list[str]) -> tuple[Pipeline, dict[str, Any]]:
    table = table.dropna(subset=["previous"])
    dates = sorted(table["date"].unique())
    if len(table) < MIN_ROWS[name] or len(dates) < 5:
        raise InsufficientHistory(f"{name}: {len(table)} usable rows over {len(dates)} service dates; "
                                  f"need at least {MIN_ROWS[name]} rows and 5 dates. Seed or collect more orders.")
    cutoff = dates[int(len(dates) * 0.8)]
    train, test = table[table["date"] < cutoff], table[table["date"] >= cutoff]
    model = pipeline(categorical).fit(train[features], train["target"])
    actual = test["target"].to_numpy()
    predicted = np.clip(model.predict(test[features]), 0, None)
    baseline = test["same_weekday_4"].to_numpy()
    metrics = {
        "mae": round(float(np.abs(actual - predicted).mean()), 3), "wape": wape(actual, predicted),
        "baseline_mae": round(float(np.abs(actual - baseline).mean()), 3), "baseline_wape": wape(actual, baseline),
        "train_rows": len(train), "test_rows": len(test), "test_from": str(pd.Timestamp(cutoff).date()),
    }
    metrics["beats_baseline"] = metrics["mae"] <= metrics["baseline_mae"]
    return pipeline(categorical).fit(table[features], table["target"]), metrics


def train(db: Any) -> dict[str, Any]:
    orders = list(db.orders.find({"status": {"$ne": "cancelled"}},
                                 {"_id": 0, "date": 1, "meal_period": 1, "user_id": 1, "source": 1,
                                  "items.dish_id": 1, "items.quantity": 1}))
    lines = order_lines(orders)
    if lines.empty:
        raise InsufficientHistory("No order history yet. Run `python -m backend.seed --history` for demo data.")
    dishes_by_period: dict[str, list[str]] = {}
    for recipe in db.recipes.find({}, {"dish_id": 1, "meal_periods": 1}):
        for period in recipe.get("meal_periods", []):
            dishes_by_period.setdefault(period, []).append(recipe["dish_id"])

    customer_model, customer_metrics = fit_and_evaluate(
        "customer_demand", add_features(customer_table(lines), ["meal_period"]), CUSTOMER_FEATURES, ["meal_period"])
    dish_model, dish_metrics = fit_and_evaluate(
        "dish_demand", add_features(dish_table(lines, dishes_by_period), ["meal_period", "dish_id"]),
        DISH_FEATURES, ["dish_id", "meal_period"])

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(customer_model, ARTIFACT_DIR / "customer_demand.joblib", compress=3)
    joblib.dump(dish_model, ARTIFACT_DIR / "dish_demand.joblib", compress=3)
    metadata = {
        "model_version": MODEL_VERSION, "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__, "orders_used": len(orders),
        "demo_order_share": round(100 * sum(o.get("source") == "demo_seed" for o in orders) / len(orders), 1),
        "history_from": str(lines["date"].min().date()), "history_to": str(lines["date"].max().date()),
        "customer_demand": {"features": CUSTOMER_FEATURES, "target": "distinct customers per service",
                            **customer_metrics},
        "dish_demand": {"features": DISH_FEATURES, "target": "portions per dish per service", **dish_metrics},
    }
    (ARTIFACT_DIR / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":
    from backend.app.core.database import get_db, init_client

    init_client()
    print(json.dumps(train(get_db()), indent=2))
