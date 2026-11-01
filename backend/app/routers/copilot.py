"""Read-only operational copilot: live MongoDB facts, phrased by the LLM when configured, else by rules."""

import json
import logging
import os
import re
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.analytics import inventory_kpis, last_days, order_kpis, orders_between, rating_kpis
from ..core.common import MEAL_PERIODS, now_utc, require_manager, today
from ..core.database import get_db
from .forecasts import ForecastRequest, run as run_forecast
from .inventory import stock_risk

router = APIRouter()
logger = logging.getLogger(__name__)
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

SUGGESTED = [
    "Which ingredients are critical?",
    "Which dishes are affected by low paneer stock?",
    "What are today's highest-selling dishes?",
    "What is tomorrow's expected lunch demand?",
    "How much revenue is at risk from stockouts today?",
    "Which healthy categories are increasing?",
    "What is the recommendation conversion rate?",
]


class CopilotRequest(BaseModel):
    question: str = Field(min_length=2, max_length=300)


def _stock(db: Any) -> tuple[str, list[str]]:
    alerts = inventory_kpis(db)["inventory_alerts"]
    if not alerts:
        return "All ingredients are above their reorder points.", []
    lines = [f"{a['name']}: {a['quantity']:g} {a['unit']} (reorder at {a['reorder_point']:g}) - {a['status']}"
             for a in alerts]
    return f"{len(alerts)} ingredient(s) need attention. Replenish {alerts[0]['name']} first.", lines


def _affected(db: Any, question: str) -> tuple[str, list[str]] | None:
    for item in db.ingredients.find({}):
        name = item["name"].lower()
        if name in question or name.split()[-1] in question.split():
            dishes = [r["name"] for r in db.recipes.find({"ingredients.ingredient_id": item["ingredient_id"]})]
            return (f"{item['name']} ({item['quantity']:g} {item['unit']}) is used in {len(dishes)} dish(es).",
                    dishes)
    return None


def _top(db: Any) -> tuple[str, list[str]]:
    kpis = order_kpis(list(db.orders.find({"date": today()})))
    if not kpis["top_dishes"]:
        return "No orders have been placed today yet.", []
    top = kpis["top_dishes"][0]
    return (f"{top['name']} leads today with {top['portions']} portions across {kpis['orders']} orders.",
            [f"{d['name']}: {d['portions']} portions" for d in kpis["top_dishes"]])


def _forecast_target(question: str) -> tuple[date, str | None]:
    words = set(question.split())
    period = next((p for p in MEAL_PERIODS if p in words), None)
    if found := re.search(r"\d{4}-\d{2}-\d{2}", question):
        try:
            return date.fromisoformat(found.group()), period
        except ValueError:
            pass
    if "today" in words or "tonight" in words:
        return date.today(), period
    for index, name in enumerate(WEEKDAYS):
        if name in words:
            return date.today() + timedelta(days=(index - date.today().weekday() - 1) % 7 + 1), period
    return date.today() + timedelta(days=1), period


def _forecast(db: Any, question: str) -> tuple[str, list[str]]:
    target, period = _forecast_target(question)
    forecast = db.forecasts.find_one({"date": target.isoformat(), "meal_period": period}, sort=[("created_at", -1)])
    # Compute on the fly without saving so the copilot stays read-only.
    forecast = forecast or run_forecast(db, ForecastRequest(date=target, meal_period=period))
    lines = [f"{d['name']} ({d['meal_period']}): expect {d['expected_orders']:g}, prepare {d['recommended_preparation']}"
             for d in sorted(forecast["dishes"], key=lambda d: -d["expected_orders"])[:6]]
    lines += [f"Shortfall: {s['name']} {s['shortfall']:g} {s['unit']}" for s in forecast["shortfalls"][:5]]
    scope = f"{period} on {target:%A %d %b}" if period else f"{target:%A %d %b} (all meals)"
    shortfall = (f" {len(forecast['shortfalls'])} ingredient shortfall(s) to fix first." if forecast["shortfalls"]
                 else " Stock covers the plan.")
    return (f"For {scope}: about {forecast['expected_customers']} customers and "
            f"Rs {forecast['projected_order_value']:,.0f} projected order value "
            f"({forecast['method'].replace('_', ' ')}).{shortfall}", lines)


def _risk(db: Any) -> tuple[str, list[str]]:
    risk = stock_risk({}, db)
    lines = [f"{r['name']}: {r['risk'].replace('_', ' ').lower()} on {r['limiting_ingredient']}, "
             f"{r['portions_possible']} portions left vs {r['expected_demand']:g} expected, "
             f"Rs {r['revenue_at_risk']:,.0f} at risk" + (f"; swap with {', '.join(r['swap_suggestions'])}"
                                                        if r["swap_suggestions"] else "")
             for r in risk["dishes_at_risk"][:6]]
    lines += [f"Waste risk: {s['name']} ({s['meal_period']}) expected {s['expected_demand']:g}" for s in risk["slow_movers"][:3]]
    if not risk["dishes_at_risk"]:
        return "No menu dish is at stock risk today.", lines
    return (f"{len(risk['dishes_at_risk'])} dish(es) at risk today with Rs {risk['revenue_at_risk']:,.0f} potential "
            f"lost revenue ({risk['demand_basis']}).", lines)


def _healthy(db: Any) -> tuple[str, list[str]]:
    start, end = last_days(14)
    mid = start + timedelta(days=7)
    previous = order_kpis([o for o in orders_between(db, start, end) if o["date"] < mid.isoformat()])
    current = order_kpis(orders_between(db, mid, end))
    change = round(current["healthy_meal_adoption"] - previous["healthy_meal_adoption"], 1)
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return (f"Healthy-meal adoption is {current['healthy_meal_adoption']}% over the last 7 days, "
            f"{direction} {abs(change)} points versus the week before.",
            [f"Previous 7 days: {previous['healthy_meal_adoption']}%", f"Last 7 days: {current['healthy_meal_adoption']}%"])


def _conversion(db: Any) -> tuple[str, list[str]]:
    start, end = last_days(30)
    kpis = order_kpis(orders_between(db, start, end))
    return (f"{kpis['recommendation_share']}% of portions ordered in the last 30 days were recommended dishes.",
            [f"Portions ordered: {kpis['portions']}"])


def _sales(db: Any) -> tuple[str, list[str]]:
    kpis = order_kpis(list(db.orders.find({"date": today()})))
    rating = rating_kpis(db, today())["average_rating"]
    return (f"Today: {kpis['orders']} orders worth Rs {kpis['accepted_order_value']:,.0f}; "
            f"{kpis['collected_orders']} collected.",
            [f"Average order value: Rs {kpis['average_order_value']:,.0f}",
             f"Average rating today: {rating if rating is not None else 'no ratings yet'}"])


@lru_cache(maxsize=1)
def _llm() -> Any:
    import utilities  # pylint: disable=import-outside-toplevel

    if not (utilities.OPENAI_API_KEY and utilities.BASE_URL):
        return None
    return utilities.get_llm_model(model_name=os.getenv("ECOS_LLM_MODEL", utilities.MODEL_GPT_4O), temperature=0.2)


def _context(db: Any, intent: str, answer: str, evidence: list[str]) -> dict[str, Any]:
    """Compact live facts sent to the LLM; nothing personal beyond dish and ingredient names."""
    sales = order_kpis(list(db.orders.find({"date": today()})))
    risk = stock_risk({}, db)
    forecast = db.forecasts.find_one({}, sort=[("created_at", -1)], projection={"_id": 0, "date": 1, "meal_period": 1,
                                     "expected_customers": 1, "projected_order_value": 1, "shortfalls": 1})
    return {
        "today": date.today().isoformat(), "matched_topic": intent, "rule_answer": answer, "evidence": evidence,
        "sales_today": {k: sales[k] for k in ("orders", "accepted_order_value", "average_order_value", "collected_orders",
                                              "cancelled_orders", "healthy_meal_adoption", "recommendation_share",
                                              "top_dishes")},
        "average_rating_today": rating_kpis(db, today())["average_rating"],
        "inventory_alerts": inventory_kpis(db)["inventory_alerts"][:10],
        "stock_risk": {"revenue_at_risk": risk["revenue_at_risk"], "demand_basis": risk["demand_basis"],
                       "dishes": risk["dishes_at_risk"][:8], "slow_movers": risk["slow_movers"][:5]},
        "latest_saved_forecast": forecast,
    }


def _llm_answer(db: Any, question: str, intent: str, answer: str, evidence: list[str]) -> str | None:
    try:
        llm = _llm()
        if llm is None:
            return None
        from utilities import try_llm_invoke  # pylint: disable=import-outside-toplevel

        data = json.dumps(_context(db, intent, answer, evidence), default=str)
        prompt = ("You are ECOS, a cafeteria operations copilot for managers. Answer the question in at most 3 short, "
                  "crisp sentences using ONLY the JSON data. Quote numbers exactly, use Rs for money, and give one "
                  "concrete action when useful. If the data cannot answer it, say what is missing.\n"
                  f"Question: {question}\nData: {data}")
        reply = try_llm_invoke(llm, prompt)
        return reply.strip() if isinstance(reply, str) and reply.strip() else None
    except Exception as error:  # The LLM is optional; rule answers remain available.
        logger.warning("Copilot LLM unavailable: %s", error)
        return None


@router.post("/copilot")
def ask(payload: CopilotRequest, _: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    question = re.sub(r"[^a-z0-9 -]", " ", payload.question.lower())
    words = set(question.split())
    if words & {"affected", "affect", "affects", "uses", "dependent"} and (hit := _affected(db, question)):
        intent, (answer, evidence) = "affected_dishes", hit
    elif words & {"risk", "lost", "loss", "losing", "waste", "wastage", "overdemand", "shortage", "swap"}:
        intent, (answer, evidence) = "stock_risk", _risk(db)
    elif words & {"critical", "stockout", "stockouts", "reorder", "replenish", "stock", "low", "inventory", "attention"}:
        intent, (answer, evidence) = "inventory_alerts", _stock(db)
    elif words & {"forecast", "demand", "tomorrow", "expected", "prepare", "preparation", "predict"}:
        intent, (answer, evidence) = "forecast", _forecast(db, question)
    elif words & {"healthy", "wellness", "protein", "fibre", "fiber"}:
        intent, (answer, evidence) = "healthy_trend", _healthy(db)
    elif words & {"recommendation", "recommendations", "conversion", "recommended"}:
        intent, (answer, evidence) = "recommendation_conversion", _conversion(db)
    elif words & {"top", "selling", "popular", "best", "highest"}:
        intent, (answer, evidence) = "top_dishes", _top(db)
    elif words & {"sales", "revenue", "value", "orders", "rating"}:
        intent, (answer, evidence) = "sales_summary", _sales(db)
    else:
        intent, answer, evidence = "unknown", "I can answer about stock, affected dishes, revenue at risk, sales, " \
                                              "forecasts, healthy trends and recommendations.", SUGGESTED
    llm_reply = _llm_answer(db, payload.question, intent, answer, evidence)
    return {"intent": intent, "answer": llm_reply or answer, "evidence": [] if llm_reply and intent == "unknown"
            else evidence, "source": "llm" if llm_reply else "rules", "read_only": True, "as_of": now_utc().isoformat()}


@router.get("/copilot/suggestions")
def suggestions() -> dict:
    return {"suggestions": SUGGESTED}
