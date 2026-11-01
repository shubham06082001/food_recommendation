"""Serve the trained demand models; returns None so callers fall back to the baseline."""

from __future__ import annotations

import json
import logging
from datetime import date
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

from ml.features import CUSTOMER_FEATURES, DISH_FEATURES, add_features, customer_table, dish_table, order_lines
from ml.train import ARTIFACT_DIR

logger = logging.getLogger(__name__)


class Predictor:
    def __init__(self, load: bool = True) -> None:
        self.metadata: dict[str, Any] | None = None
        self.models: dict[str, Any] = {}
        path = ARTIFACT_DIR / "model_metadata.json"
        if not load or not path.exists():
            return
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if metadata.get("sklearn_version") != sklearn.__version__:
            logger.warning("Ignoring models trained with sklearn %s (running %s); retrain them.",
                           metadata.get("sklearn_version"), sklearn.__version__)
            return
        self.metadata = metadata
        # Artifacts are produced by ml.train in our own folder; never load user-supplied files (pickle).
        self.models = {name: joblib.load(ARTIFACT_DIR / f"{name}.joblib") for name in ("customer_demand", "dish_demand")
                       if metadata[name].get("beats_baseline")}

    def predict(self, orders: list[dict], period: str, target: date, dish_ids: list[str]) -> dict[str, Any] | None:
        """Customers and portions per dish for one service; dishes without history are omitted."""
        if not self.models:
            return None
        lines = order_lines(orders)
        lines = lines[lines["meal_period"] == period]
        if lines.empty:
            return None
        when = pd.Timestamp(target)
        result: dict[str, Any] = {"customers": None, "dishes": {}}
        if model := self.models.get("customer_demand"):
            table = pd.concat([customer_table(lines), pd.DataFrame([{"date": when, "meal_period": period}])])
            row = add_features(table, ["meal_period"]).query("date == @when")
            if row["previous"].notna().all():
                result["customers"] = float(np.clip(model.predict(row[CUSTOMER_FEATURES])[0], 0, None))
        if (model := self.models.get("dish_demand")) and dish_ids:
            target_rows = pd.DataFrame([{"date": when, "meal_period": period, "dish_id": d} for d in dish_ids])
            table = pd.concat([dish_table(lines, {period: dish_ids}), target_rows])
            rows = add_features(table, ["meal_period", "dish_id"]).query("date == @when and previous.notna()",
                                                                         engine="python")
            if not rows.empty:
                predicted = np.clip(model.predict(rows[DISH_FEATURES]), 0, None)
                result["dishes"] = dict(zip(rows["dish_id"], map(float, predicted)))
        return result


@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    try:
        return Predictor()
    except (OSError, ValueError, KeyError) as error:
        logger.warning("Demand models unavailable: %s", error)
        return Predictor(load=False)


def reload_predictor() -> Predictor:
    get_predictor.cache_clear()
    return get_predictor()
