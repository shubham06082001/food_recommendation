import io
import math
from collections import defaultdict
from typing import Any, Literal

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..core.common import MEAL_PERIODS, now_utc, nutrition_tags, record_movement, require_manager
from ..core.database import get_db
from ..core.enrich import enrich_in_background

router = APIRouter()

MAX_BYTES = 5 * 1024 * 1024
INVENTORY_COLUMNS = ["ingredient_id", "name", "quantity", "unit", "reorder_point"]
RECIPE_COLUMNS = ["dish_id", "dish_name", "ingredient_id", "quantity_per_portion"]
DIETS = {"veg", "egg", "non_veg"}


async def read_table(file: UploadFile, required: list[str]) -> pd.DataFrame:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 5 MB")
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            frame = pd.read_csv(io.BytesIO(content))
        elif name.endswith((".xlsx", ".xls")):
            frame = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Upload a .xlsx or .csv file")
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=f"Could not read file: {error}") from error
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")
    if frame.empty:
        raise HTTPException(status_code=400, detail="File has no rows")
    return frame


def number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(result) or not math.isfinite(result) else result


def text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


@router.post("/upload/inventory")
async def upload_inventory(
    file: UploadFile = File(...), mode: Literal["validate", "commit"] = Form("commit"),
    manager: dict = Depends(require_manager), db: Any = Depends(get_db),
) -> dict:
    frame = await read_table(file, INVENTORY_COLUMNS)
    rows, errors, seen = [], [], set()
    for index, raw in frame.iterrows():
        line = index + 2
        ingredient_id = text(raw["ingredient_id"]).upper()
        quantity, reorder = number(raw["quantity"]), number(raw["reorder_point"])
        if not ingredient_id or not text(raw["name"]) or not text(raw["unit"]):
            errors.append(f"Row {line}: ingredient_id, name and unit are required")
        elif ingredient_id in seen:
            errors.append(f"Row {line}: duplicate ingredient_id {ingredient_id}")
        elif quantity is None or quantity < 0 or reorder is None or reorder < 0:
            errors.append(f"Row {line}: quantity and reorder_point must be non-negative numbers")
        else:
            seen.add(ingredient_id)
            rows.append({"ingredient_id": ingredient_id, "name": text(raw["name"]), "quantity": quantity,
                         "unit": text(raw["unit"]), "reorder_point": reorder})
            if text(raw.get("category")):
                rows[-1]["category"] = text(raw.get("category"))[:60]
    if errors or mode == "validate":
        return {"success": not errors, "mode": mode, "valid_rows": len(rows), "errors": errors[:50]}

    for row in rows:
        previous = db.ingredients.find_one({"ingredient_id": row["ingredient_id"]}) or {}
        db.ingredients.update_one({"ingredient_id": row["ingredient_id"]},
                                  {"$set": {**row, "updated_at": now_utc()}}, upsert=True)
        delta = row["quantity"] - float(previous.get("quantity", 0))
        if delta:
            record_movement(db, row["ingredient_id"], "stock_upload", delta, manager["user_id"])
    return {"success": True, "mode": mode, "updated": len(rows), "errors": []}


@router.post("/upload/recipes")
async def upload_recipes(
    file: UploadFile = File(...), mode: Literal["validate", "commit"] = Form("commit"),
    _: dict = Depends(require_manager), db: Any = Depends(get_db),
) -> dict:
    frame = await read_table(file, RECIPE_COLUMNS)
    known = {i["ingredient_id"]: i for i in db.ingredients.find({}, {"ingredient_id": 1, "unit": 1})}
    dishes: dict[str, dict[str, Any]] = {}
    lines: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors = []
    for index, raw in frame.iterrows():
        line = index + 2
        dish_id, ingredient_id = text(raw["dish_id"]).upper(), text(raw["ingredient_id"]).upper()
        quantity = number(raw["quantity_per_portion"])
        if not dish_id or not text(raw["dish_name"]):
            errors.append(f"Row {line}: dish_id and dish_name are required")
            continue
        if ingredient_id not in known:
            errors.append(f"Row {line}: unknown ingredient_id {ingredient_id or '(blank)'}; upload inventory first")
            continue
        if quantity is None or quantity <= 0:
            errors.append(f"Row {line}: quantity_per_portion must be positive")
            continue
        if dish_id not in dishes:
            diet = text(raw.get("diet", "veg")).lower() or "veg"
            periods = [p.strip().lower() for p in text(raw.get("meal_periods", "lunch")).split("|") if p.strip()]
            if diet not in DIETS or not periods or any(p not in MEAL_PERIODS for p in periods):
                errors.append(f"Row {line}: diet must be veg/egg/non_veg; meal_periods like 'lunch|dinner'")
                continue
            nutrition = {k: number(raw.get(k)) or 0.0 for k in ("protein_g", "fibre_g", "sodium_mg", "energy_kcal")}
            dishes[dish_id] = {
                "dish_id": dish_id, "name": text(raw["dish_name"]), "price": number(raw.get("price")) or 0.0,
                "diet": diet, "meal_periods": periods, "catalog_code": text(raw.get("catalog_code")) or None,
                "declared_allergens": [a.strip().lower() for a in text(raw.get("allergens")).split("|") if a.strip()],
                "nutrition": nutrition, "nutrition_tags": nutrition_tags(**nutrition),
                "evidence_status": text(raw.get("evidence_status")).lower() or "confirmed", "source": "manager",
            }
            image = text(raw.get("image_url"))
            if image.startswith("https://"):
                dishes[dish_id].update({"image_url": image, "image_source": "manager"})
        lines[dish_id].append({"ingredient_id": ingredient_id, "quantity": quantity,
                               "unit": known[ingredient_id].get("unit")})
    if errors or mode == "validate":
        return {"success": not errors, "mode": mode, "dishes": len(dishes), "errors": errors[:50]}

    for dish_id, dish in dishes.items():
        # Nutrients are re-derived from the (possibly new) catalog code by the background enrichment.
        db.recipes.update_one({"dish_id": dish_id},
                              {"$set": {**dish, "ingredients": lines[dish_id], "updated_at": now_utc()},
                               "$setOnInsert": {"on_menu": True}, "$unset": {"nutrient_profile": ""}}, upsert=True)
    enrich_in_background(db)
    return {"success": True, "mode": mode, "updated": len(dishes), "errors": []}
