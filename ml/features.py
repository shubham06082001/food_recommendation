"""Feature engineering shared by training and serving so both see identical inputs."""

from __future__ import annotations

import pandas as pd

CUSTOMER_FEATURES = ["meal_period", "day_of_week", "previous", "rolling_4", "same_weekday_4"]
DISH_FEATURES = ["dish_id", *CUSTOMER_FEATURES]


def order_lines(orders: list[dict]) -> pd.DataFrame:
    """One row per ordered dish line of non-cancelled orders."""
    rows = [{"date": o["date"], "meal_period": o["meal_period"], "user_id": o["user_id"],
             "dish_id": i["dish_id"], "quantity": i["quantity"]} for o in orders for i in o.get("items", [])]
    frame = pd.DataFrame(rows, columns=["date", "meal_period", "user_id", "dish_id", "quantity"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def customer_table(lines: pd.DataFrame) -> pd.DataFrame:
    return (lines.groupby(["date", "meal_period"], as_index=False)
            .agg(target=("user_id", "nunique")))


def dish_table(lines: pd.DataFrame, dishes_by_period: dict[str, list[str]]) -> pd.DataFrame:
    """Portions per service and dish, including zero-sale days for dishes offered in that period."""
    services = lines[["date", "meal_period"]].drop_duplicates()
    offered = pd.DataFrame([(p, d) for p, ids in dishes_by_period.items() for d in ids],
                           columns=["meal_period", "dish_id"])
    sold = lines.groupby(["date", "meal_period", "dish_id"], as_index=False)["quantity"].sum()
    grid = services.merge(offered, on="meal_period")
    table = grid.merge(sold, on=["date", "meal_period", "dish_id"], how="outer").fillna({"quantity": 0})
    return table.rename(columns={"quantity": "target"})


def add_features(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Lag features use only earlier services of the same group (no leakage)."""
    table = table.sort_values("date").reset_index(drop=True)
    table["day_of_week"] = table["date"].dt.dayofweek
    shifted = table.groupby(keys)["target"].shift(1)
    table["previous"] = shifted
    table["rolling_4"] = shifted.groupby([table[k] for k in keys]).transform(
        lambda s: s.rolling(4, min_periods=1).mean())
    weekday_shift = table.groupby([*keys, "day_of_week"])["target"].shift(1)
    table["same_weekday_4"] = weekday_shift.groupby([table[k] for k in [*keys, "day_of_week"]]).transform(
        lambda s: s.rolling(4, min_periods=1).mean()).fillna(table["rolling_4"])
    return table
