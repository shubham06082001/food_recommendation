"""Employee workspace: home, menu and recommendations, orders and feedback, monthly wellness."""

from __future__ import annotations

import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from dashboard import api
from dashboard.config import DISCLAIMER, MEAL_PERIODS, TAG_LABELS
from dashboard.state import add_to_cart, go_to
from dashboard.utils import money

STATUS_STEPS = ["confirmed", "preparing", "ready", "collected"]
HTTPS = "https://"
MENU_PAGE_SIZE = 12


def _recommendations(meal_period: str, query: str = "", limit: int = 6, offset: int = 0) -> dict | None:
    try:
        return api.recommendations(st.session_state["user_id"], meal_period, query, limit, offset)
    except api.ApiError as error:
        st.error(str(error), icon=":material/error:")
        return None


def _period_now() -> str:
    hour = datetime.now().hour
    return "breakfast" if hour < 11 else "lunch" if hour < 15 else "snacks" if hour < 18 else "dinner"


def _amounts(dish: dict) -> dict[str, float]:
    profile = dish.get("nutrient_profile") or {}
    values = {row["key"]: row["amount"] for row in profile.get("macros", [])}
    return {**values, **{k: v for k, v in dish.get("nutrition", {}).items() if v}}


def _card_html(dish: dict, score: int | None) -> str:
    name = html.escape(dish["name"])
    image = dish.get("image_url") or ""
    top = (f'<img class="gt-card-img" src="{html.escape(image)}" alt="{name}" loading="lazy" decoding="async" '
           f'width="330" height="170" referrerpolicy="no-referrer">'
           if image.startswith(HTTPS) else '<div class="gt-card-noimg">🍽️</div>')
    if image.startswith(HTTPS) and dish.get("image_credit", "").startswith(HTTPS):
        top += (f'<div class="gt-credit"><a href="{html.escape(dish["image_credit"])}" target="_blank" '
                f'rel="noopener">Photo: Wikimedia Commons</a></div>')
    values = _amounts(dish)
    macros = "".join(f"<div><b>{values.get(k, 0):.0f}{unit}</b><small>{label}</small></div>" for k, unit, label in (
        ("protein_g", "g", "protein"), ("carb_g", "g", "carbs"), ("fat_g", "g", "fat"), ("energy_kcal", "", "kcal")))
    portions = dish.get("maximum_portions")
    status = "Unavailable" if not dish.get("available", True) else (
        f"Only {portions} left" if portions is not None and portions < 5 else "Available now")
    allergens = dish.get("declared_allergens") or []
    chips = "".join(f'<span class="gt-chip warn">{html.escape(a.title())}</span>' for a in allergens) or \
        '<span class="gt-chip">No declared allergens</span>'
    chips += "".join(f'<span class="gt-chip">{TAG_LABELS[t]}</span>' for t in dish.get("nutrition_tags", [])
                     if t in TAG_LABELS)
    badge = f'<span class="gt-score">{score} match</span>' if score else ""
    return (f'{top}<div class="gt-card-head"><span class="gt-card-name">{name}</span>{badge}</div>'
            f'<div class="gt-card-sub">{money(dish["price"])} · {status} · '
            f'{html.escape(dish.get("diet", "").replace("_", "-"))} · {values.get("fibre_g", 0):.0f} g fibre</div>'
            f'<div class="gt-macros">{macros}</div><div class="gt-chips">{chips}</div>')


def _nutrient_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"Nutrient": r["label"], "Amount": f"{r['amount']:g} {r['unit']}",
                          "% of a day": min(r["daily_pct"], 100.0)} for r in rows])


def nutrition_detail(dish: dict) -> None:
    profile = dish.get("nutrient_profile")
    st.markdown(f"**{dish['name']}**")
    if not profile:
        nutrition = dish.get("nutrition", {})
        st.caption("Detailed nutrients are not linked for this dish yet (add an INDB catalog code).")
        st.write(", ".join(f"{k.replace('_', ' ')}: {v:g}" for k, v in nutrition.items()))
        return
    st.caption(f"{profile['basis'].capitalize()} · source {profile['source']}. % of a day uses approximate adult "
               "reference values; guidance only.")
    config = {"% of a day": st.column_config.ProgressColumn("% of a day", min_value=0, max_value=100, format="%.0f%%")}
    macro_tab, micro_tab = st.tabs(["Macronutrients", "Vitamins & minerals"])
    macro_tab.dataframe(_nutrient_frame(profile["macros"]), hide_index=True, column_config=config)
    micro_tab.dataframe(_nutrient_frame(profile["micros"]), hide_index=True, column_config=config)


def dish_card(dish: dict, key: str, reasons: list[str] | None = None) -> None:
    with st.container(border=True):
        st.html(_card_html(dish, dish.get("match_percent") if reasons is not None else None))
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
        with st.popover("Macro & micronutrients", key=f"nut_{key}", icon=":material/nutrition:", width="stretch"):
            nutrition_detail(dish)


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


def _show_more(key: tuple, step: int) -> None:
    offsets = st.session_state.setdefault("gt_offsets", {})
    offsets[key] = offsets.get(key, 0) + step


def _reset_seen(key: tuple) -> None:
    st.session_state.setdefault("gt_offsets", {}).pop(key, None)
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
    mode = st.segmented_control("View", ["For you", "Plan my day", "Full menu"], default="For you",
                                key="gt_menu_mode") or "For you"
    if mode == "Plan my day":
        _render_day_plan()
        st.caption(DISCLAIMER)
        return
    period = st.segmented_control("Meal period", MEAL_PERIODS, default=_period_now(), format_func=str.title,
                                  key="gt_period_select") or _period_now()
    if mode == "Full menu":
        _render_full_menu(period)
    else:
        _render_for_you(period)
    st.caption(DISCLAIMER)


def _render_for_you(period: str) -> None:
    with st.form("rec_query", border=False):
        cols = st.columns((4, 1), vertical_alignment="bottom")
        query = cols[0].text_input("What would you like?", placeholder="e.g. light high-protein lunch under 150, no milk",
                                   max_chars=200)
        cols[1].form_submit_button("Search", icon=":material/search:", width="stretch")

    query = query.strip()
    key = (period, query)
    offset = st.session_state.setdefault("gt_offsets", {}).get(key, 0)
    recs = _recommendations(period, query, offset=offset)
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
                          on_click=_show_more, args=(key, len(recs["items"])))
        actions[1].button("Refresh", icon=":material/refresh:", on_click=_reset_seen, args=(key,))
        if recs["items"]:
            cols = st.columns(3)
            for index, dish in enumerate(recs["items"]):
                with cols[index % 3]:
                    dish_card(dish, f"rec_{period}_{dish['dish_id']}", dish["reasons"])
        elif offset:
            st.info("You've seen every match. Press Refresh to start over.", icon=":material/info:")
        else:
            st.info("No dishes match your preferences and search for this meal period.", icon=":material/info:")


def _turn_page(key: str, step: int) -> None:
    st.session_state[key] = max(0, st.session_state.get(key, 0) + step)


def _render_full_menu(period: str) -> None:
    query = st.text_input("Search the menu", placeholder="e.g. paneer, idli, soup", max_chars=80,
                          key="gt_menu_search", icon=":material/search:").strip()
    page_key = f"gt_menu_page_{period}_{query}"
    page = st.session_state.get(page_key, 0)
    try:
        menu = api.menu_page(st.session_state["user_id"], period, query, MENU_PAGE_SIZE, page * MENU_PAGE_SIZE)
    except api.ApiError as error:
        st.error(str(error), icon=":material/cloud_off:")
        return
    if menu["catalog_empty"]:
        st.info("The menu is being prepared from the food catalog. This takes a moment on a new database.",
                icon=":material/hourglass_top:")
        st.button("Check again", icon=":material/refresh:", on_click=api.menu_page.clear)
        return
    total = menu["total"]
    st.markdown(f"#### Full {period} menu")
    st.caption(f"{total} dish(es)" + (f" matching “{query}”" if query else ""))
    if not menu["items"]:
        st.info("No dishes found.", icon=":material/info:")
    cols = st.columns(3)
    for index, dish in enumerate(menu["items"]):
        with cols[index % 3]:
            dish_card(dish, f"menu_{period}_{dish['dish_id']}")
    last_page = max(0, (total - 1) // MENU_PAGE_SIZE)
    nav = st.columns((1, 1, 4), vertical_alignment="center")
    nav[0].button("Previous", icon=":material/chevron_left:", disabled=page == 0, key="gt_menu_prev",
                  on_click=_turn_page, args=(page_key, -1), width="stretch")
    nav[1].button("Next", icon=":material/chevron_right:", disabled=page >= last_page, key="gt_menu_next",
                  on_click=_turn_page, args=(page_key, 1), width="stretch")
    nav[2].caption(f"Page {page + 1} of {last_page + 1}")


def _add_plan(meals: list[dict]) -> None:
    for meal in meals:
        add_to_cart({**meal, "from_recommendation": True})


def _render_day_plan() -> None:
    with st.form("plan_query", border=False):
        cols = st.columns((4, 1), vertical_alignment="bottom")
        query = cols[0].text_input("Shape the plan (optional)", placeholder="e.g. high protein, under 150, no milk",
                                   max_chars=200)
        cols[1].form_submit_button("Build plan", icon=":material/auto_awesome:", width="stretch")
    try:
        plan = api.meal_plan(st.session_state["user_id"], query.strip())
    except api.ApiError as error:
        st.error(str(error), icon=":material/error:")
        return
    meals = plan["meals"]
    if not meals:
        st.info("No dishes fit your preferences today.", icon=":material/info:")
        return
    st.caption("One live pick per meal, chosen by the recommendation engine around your diet, allergens and goals.")
    cols = st.columns(len(meals))
    for col, meal in zip(cols, meals):
        with col:
            st.markdown(f"**{meal['meal_period'].title()}**")
            dish_card(meal, f"plan_{meal['meal_period']}_{meal['dish_id']}", meal["reasons"][:2])
    totals = plan["totals"]
    with st.container(border=True):
        head = st.columns((3, 1), vertical_alignment="center")
        head[0].markdown(f"#### Your day in nutrients · {money(totals['price'])}")
        head[1].button("Add whole plan", icon=":material/add_shopping_cart:", type="primary", width="stretch",
                       on_click=_add_plan, args=(meals,))
        macros = {r["key"]: r for r in totals["macros"]}
        metrics = st.columns(5)
        for col, key in zip(metrics, ("energy_kcal", "protein_g", "carb_g", "fat_g", "fibre_g")):
            row = macros[key]
            col.metric(row["label"], f"{row['amount']:.0f} {row['unit']}", f"{row['daily_pct']:.0f}% of a day",
                       delta_color="off")
        config = {"% of a day": st.column_config.ProgressColumn("% of a day", min_value=0, max_value=100,
                                                                format="%.0f%%")}
        left, right = st.columns(2)
        left.dataframe(_nutrient_frame(totals["macros"]), hide_index=True, column_config=config)
        right.dataframe(_nutrient_frame(totals["micros"]), hide_index=True, column_config=config)
        st.caption("Totals are per cafeteria portion from the Indian Nutrient Databank; reference values are "
                   "approximate adult daily needs and not medical advice.")


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
