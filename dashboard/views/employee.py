"""Employee workspace: home, menu and recommendations, orders and feedback, monthly wellness."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from dashboard import api
from dashboard.config import DISCLAIMER, MEAL_PERIODS, TAG_LABELS
from dashboard.state import add_to_cart, go_to
from dashboard.utils import money, tag_badges

STATUS_STEPS = ["confirmed", "preparing", "ready", "collected"]


def _recommendations(meal_period: str, query: str = "", limit: int = 6, exclude: tuple = ()) -> dict | None:
    try:
        return api.recommendations(st.session_state["user_id"], meal_period, query, limit, exclude)
    except api.ApiError as error:
        st.error(str(error), icon=":material/error:")
        return None


def _period_now() -> str:
    hour = datetime.now().hour
    return "breakfast" if hour < 11 else "lunch" if hour < 15 else "snacks" if hour < 18 else "dinner"


def dish_card(dish: dict, key: str, reasons: list[str] | None = None) -> None:
    with st.container(border=True):
        top = st.columns((3, 1), vertical_alignment="center")
        top[0].markdown(f"**{dish['name']}**")
        top[1].markdown(f"**{money(dish['price'])}**")
        if reasons is not None and dish.get("match_percent"):
            st.caption(f"{dish['match_percent']}% match for you")
        nutrition = dish.get("nutrition", {})
        st.caption(f"{nutrition.get('protein_g', 0):.0f} g protein · {nutrition.get('fibre_g', 0):.0f} g fibre · "
                   f"{nutrition.get('energy_kcal', 0):.0f} kcal · {dish.get('diet', '').replace('_', '-')}")
        if dish.get("nutrition_tags"):
            st.markdown(tag_badges(dish["nutrition_tags"]))
        allergens = ", ".join(dish.get("declared_allergens", [])) or "none declared"
        st.caption(f"Declared allergens: {allergens}")
        for reason in reasons or []:
            st.caption(f":material/check: {reason}")
        available = dish.get("available", True)
        eligible = dish.get("eligible", True)
        if not available:
            st.markdown(f":red-badge[Unavailable] {dish.get('unavailable_reason', '')}")
        elif not eligible:
            st.markdown(f":orange-badge[Not for you] {dish.get('eligibility_note', '')}")
        st.button("Add to cart", key=key, icon=":material/add_shopping_cart:", type="primary",
                  disabled=not (available and eligible), on_click=add_to_cart,
                  args=({**dish, "from_recommendation": reasons is not None},), width="stretch")


def _status_line(order: dict) -> None:
    if order["status"] == "cancelled":
        st.markdown(":red-badge[Cancelled]")
        return
    step = STATUS_STEPS.index(order["status"])
    st.progress((step + 1) / len(STATUS_STEPS), text=f"Status: {order['status'].title()}")


def render_employee_home() -> None:
    data = api.load(f"/dashboard/employee/{st.session_state['user_id']}")
    if data is None:
        return
    st.caption(date.today().strftime("%A, %d %B"))
    st.title(f"Hello, {data['name']}")
    if not data["profile_complete"]:
        with st.container(border=True):
            st.markdown("#### Personalise your meals")
            st.caption("Set your dietary preference, wellness goals and allergen exclusions to get recommendations "
                       "made for you. You can browse the menu without them.")
            st.button("Complete my preferences", type="primary", icon=":material/settings:",
                      on_click=go_to, args=("Profile",))

    period = data["current_meal_period"]
    left, right = st.columns((2.1, 1))
    with left:
        st.markdown(f"#### Recommended for {period}")
        recs = _recommendations(period, limit=3)
        if recs and recs["items"]:
            cols = st.columns(3)
            for col, dish in zip(cols, recs["items"][:3]):
                with col:
                    dish_card(dish, f"home_{dish['dish_id']}", dish["reasons"][:2])
        elif recs is not None:
            st.info(f"No eligible {period} dishes are available right now.", icon=":material/info:")
        st.button("Explore full menu", icon=":material/restaurant_menu:", on_click=go_to, args=("Menu",))
    with right:
        with st.container(border=True):
            st.caption("Active order")
            order = data["active_order"]
            if order:
                st.markdown(f"#### Pickup {order['pickup_reference']}")
                st.caption(", ".join(f"{i['name']} × {i['quantity']}" for i in order["items"]))
                _status_line(order)
            else:
                st.markdown("No active order")
        with st.container(border=True):
            summary = data.get("wellness_summary") or {}
            st.caption(f"Wellness this month · {summary.get('meals_tracked', 0)} meals tracked")
            st.metric("Wellness score", f"{summary.get('wellness_score', 20)} / 100")
            categories = summary.get("categories") or {}
            protein = categories.get("high_protein", {"percentage": 0.0})
            fibre = categories.get("high_fibre", {"percentage": 0.0})
            cols = st.columns(2)
            cols[0].metric("High protein", f"{protein['percentage']:.0f}%", _delta(protein))
            cols[1].metric("High fibre", f"{fibre['percentage']:.0f}%", _delta(fibre))
            st.button("View my scorecard", icon=":material/monitor_heart:", on_click=go_to, args=("My wellness",))
        previous = data["previous_order"]
        if previous:
            with st.container(border=True):
                st.caption("Previous order")
                st.markdown(", ".join(f"{i['name']} × {i['quantity']}" for i in previous["items"]))
                st.caption(f"{previous['date']} · {money(previous['total'])}")


def _delta(category: dict) -> str | None:
    change = category.get("change_percentage_points")
    return None if change is None else f"{change:+.1f} pts vs last month"


def _show_more(key: tuple, dish_ids: list[str]) -> None:
    seen = st.session_state.setdefault("gt_seen", {})
    seen[key] = seen.get(key, []) + dish_ids


def _reset_seen(key: tuple) -> None:
    st.session_state.setdefault("gt_seen", {}).pop(key, None)
    api.recommendations.clear()


def _understood(intent: dict) -> list[str]:
    parts = [TAG_LABELS[t] for t in intent.get("tags", [])]
    if intent.get("max_price"):
        parts.append(f"under ₹{intent['max_price']:.0f}")
    if intent.get("max_kcal"):
        parts.append(f"≤ {intent['max_kcal']} kcal")
    if intent.get("min_kcal"):
        parts.append(f"≥ {intent['min_kcal']} kcal")
    parts += [f"no {t}" for t in intent.get("excluded_terms", [])]
    return parts


def render_menu() -> None:
    st.caption("Personalised food discovery")
    st.title("Today's menu")
    period = st.segmented_control("Meal period", MEAL_PERIODS, default=_period_now(), format_func=str.title,
                                  key="gt_period_select") or _period_now()

    with st.form("rec_query", border=False):
        cols = st.columns((4, 1), vertical_alignment="bottom")
        query = cols[0].text_input("What would you like?", placeholder="e.g. light high-protein lunch",
                                   max_chars=200)
        cols[1].form_submit_button("Search", icon=":material/search:", width="stretch")

    query = query.strip()
    seen = st.session_state.setdefault("gt_seen", {})
    key = (period, query)
    recs = _recommendations(period, query, exclude=tuple(seen.get(key, [])))
    if recs:
        st.markdown("#### Recommended for you")
        mode = "Semantic ranking (Qdrant)" if recs["semantic_ranking"] else "Goal-based ranking"
        understood = " · ".join(_understood(recs["interpreted"]))
        st.caption(f"{mode}, computed live from today's stock, your profile and your order history. "
                   f"Search: “{recs['query']}”" + (f" · Understood: {understood}" if understood else ""))
        if recs["note"]:
            st.info(recs["note"], icon=":material/info:")
        actions = st.columns((1.2, 1.2, 3))
        actions[0].button("Show different options", icon=":material/shuffle:", disabled=not recs["has_more"],
                          on_click=_show_more, args=(key, [i["dish_id"] for i in recs["items"]]))
        actions[1].button("Refresh", icon=":material/refresh:", on_click=_reset_seen, args=(key,))
        if recs["items"]:
            cols = st.columns(3)
            for index, dish in enumerate(recs["items"]):
                with cols[index % 3]:
                    dish_card(dish, f"rec_{period}_{dish['dish_id']}", dish["reasons"])
        elif seen.get(key):
            st.info("You've seen every match. Press Refresh to start over.", icon=":material/info:")
        else:
            st.info("No dishes match your preferences and search for this meal period.", icon=":material/info:")

    menu = api.load("/menu", meal_period=period, user_id=st.session_state["user_id"])
    if menu is None:
        return
    st.markdown(f"#### Full {period} menu")
    if not menu["items"]:
        st.info(f"No {period} menu has been published today.", icon=":material/info:")
    cols = st.columns(3)
    for index, dish in enumerate(sorted(menu["items"], key=lambda d: (not d["available"], d["name"]))):
        with cols[index % 3]:
            dish_card(dish, f"menu_{period}_{dish['dish_id']}")
    st.caption(DISCLAIMER)


def _reorder(order: dict) -> None:
    for item in order["items"]:
        for _ in range(item["quantity"]):
            add_to_cart({"dish_id": item["dish_id"], "name": item["name"], "price": item["unit_price"]})


def render_my_orders() -> None:
    st.caption("Orders")
    st.title("My orders")
    if confirmation := st.session_state.pop("gt_last_order", None):
        st.success(f"Order placed. Pickup reference **{confirmation['pickup_reference']}** · "
                   f"{money(confirmation['total'])} (demo payment)", icon=":material/check_circle:")
    st.button("Refresh", icon=":material/refresh:")
    result = api.load("/orders")
    if result is None:
        return
    orders = result["data"]
    if not orders:
        st.info("You haven't ordered yet.", icon=":material/info:")
        st.button("Browse the menu", on_click=go_to, args=("Menu",), type="primary")
        return
    for order in orders:
        with st.container(border=True):
            top = st.columns((2, 1, 1), vertical_alignment="center")
            top[0].markdown(f"**{order['order_id']}** · pickup **{order['pickup_reference']}**")
            top[1].caption(f"{order['date']} · {order['meal_period']}")
            top[2].markdown(f"**{money(order['total'])}**")
            st.caption(", ".join(f"{i['name']} × {i['quantity']}" for i in order["items"]))
            _status_line(order)
            actions = st.columns((1, 3))
            actions[0].button("Reorder", key=f"re_{order['order_id']}", icon=":material/replay:",
                              on_click=_reorder, args=(order,))
            if order["status"] in ("ready", "collected") and not order.get("rating"):
                with actions[1].expander("Give feedback"):
                    _feedback_form(order["order_id"])
            elif order.get("rating"):
                actions[1].caption(f"Your rating: {'★' * order['rating']}")


def _feedback_form(order_id: str) -> None:
    with st.form(f"fb_{order_id}", border=False):
        rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=5, format_func=lambda n: "★" * n,
                                  key=f"stars_{order_id}")
        reason = st.selectbox("What stood out?", ["taste", "portion", "quality", "waiting_time", "other"],
                              format_func=lambda r: r.replace("_", " ").title(), key=f"reason_{order_id}")
        comment = st.text_input("Comment (optional)", max_chars=500, key=f"comment_{order_id}")
        if st.form_submit_button("Submit feedback", type="primary"):
            try:
                api.post("/feedback", {"order_id": order_id, "rating": rating, "reason": reason, "comment": comment})
            except api.ApiError as error:
                st.error(str(error))
                return
            st.toast("Thanks for your feedback", icon=":material/check_circle:")
            st.rerun()


def _month_options(count: int = 6) -> list[str]:
    first = date.today().replace(day=1)
    months = []
    for offset in range(count):
        year, month = divmod(first.year * 12 + first.month - 1 - offset, 12)
        months.append(f"{year:04d}-{month + 1:02d}")
    return months


def render_wellness() -> None:
    st.caption("Guidance, not medical advice")
    st.title("My monthly wellness")
    user_id = st.session_state["user_id"]
    month = st.selectbox("Month", _month_options(),
                         format_func=lambda m: date.fromisoformat(f"{m}-01").strftime("%B %Y"))
    data = api.load(f"/wellness/{user_id}/monthly", month=month)
    if data is None:
        return
    st.markdown(f"#### Your {date.fromisoformat(f'{month}-01').strftime('%B')} meal choices")
    st.metric("Monthly wellness score", f"{data['wellness_score']} / 100",
              help="Starts at 20 each month; +10 per healthy portion ordered, +5 per other portion (max 100).")
    if data["orders_pending_collection"]:
        st.caption(f"{data['orders_pending_collection']} order(s) will count once collected.")
    if not data["meals_tracked"]:
        st.info("No collected meals for this month yet. Your scorecard fills in as you collect orders.",
                icon=":material/info:")
    cols = st.columns(4)
    for col, (tag, values) in zip(cols, data["categories"].items()):
        col.metric(f"{TAG_LABELS[tag]} meals", f"{values['percentage']:.0f}%", _delta(values),
                   help=f"{values['meal_count']} of {data['meals_tracked']} collected portions")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### Goal progress")
            if not data["goal_progress"]:
                st.caption("Set wellness goals in your profile to track progress.")
            for goal in data["goal_progress"]:
                st.progress(min(goal["match_rate"] / 100, 1.0),
                            text=f"{TAG_LABELS.get(goal['goal'], goal['goal'])}: {goal['matching_meals']} of "
                                 f"{goal['eligible_meals']} meals matched ({goal['match_rate']:.0f}%)")
        with st.container(border=True):
            st.markdown("#### Recommendation engagement")
            engagement = data["recommendation_engagement"]
            row = st.columns(2)
            row[0].metric("Recommended meals ordered", engagement["recommended_meals_ordered"])
            row[1].metric("Share of meals from recommendations", f"{engagement['share_of_meals_recommended']:.0f}%")
    with right:
        with st.container(border=True):
            st.markdown("#### Monthly consistency")
            st.metric("Meals tracked", data["meals_tracked"])
            coverage = data["meal_period_coverage"]
            st.caption(" | ".join(f"{p.title()} {coverage.get(p, 0)}" for p in MEAL_PERIODS))
            if data["top_dishes"]:
                st.caption("Most chosen: " + ", ".join(f"{d['name']} ({d['portions']})" for d in data["top_dishes"][:3]))

    trend = api.load(f"/wellness/{user_id}/trend", months=6)
    if trend:
        frame = pd.DataFrame(trend["trend"]).rename(columns={
            "high_protein_percentage": "High protein %", "high_fibre_percentage": "High fibre %",
            "balanced_percentage": "Balanced %", "lower_sodium_percentage": "Lower sodium %"})
        with st.container(border=True):
            st.markdown("#### Six-month trend")
            st.line_chart(frame, x="month", y=["High protein %", "High fibre %", "Balanced %", "Lower sodium %"],
                          height=260)
    st.caption(data["disclaimer"])
