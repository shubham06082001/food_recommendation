"""Manager workspace: today, live orders, inventory, menu management, forecasting, executive, copilot."""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from dashboard import api
from dashboard.config import MEAL_PERIODS, NEXT_STATUS, ORDER_STATUSES, STATUS_BADGE
from dashboard.state import go_to
from dashboard.utils import money


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}%"


@st.dialog("Replenish ingredient")
def replenish_dialog(item: dict) -> None:
    st.markdown(f"**{item['name']}** · {STATUS_BADGE[item['status']]}")
    st.caption(f"On hand {item['quantity']:g} {item['unit']} · reorder point {item['reorder_point']:g} {item['unit']}")
    suggested = max(float(item["reorder_point"]) * 2 - float(item["quantity"]), 1.0)
    with st.form("replenish_form", border=False):
        quantity = st.number_input(f"Quantity to add ({item['unit']})", min_value=0.0, value=round(suggested, 1),
                                   step=100.0 if item["unit"] in ("g", "ml") else 1.0)
        note = st.text_input("Note", value="Manual replenishment", max_chars=200)
        submitted = st.form_submit_button("Confirm replenishment", type="primary", icon=":material/add_box:")
    if submitted:
        if quantity <= 0:
            st.warning("Enter a quantity greater than zero.")
            return
        try:
            result = api.post(f"/inventory/{item['ingredient_id']}/replenish", {"quantity": quantity, "note": note})
        except api.ApiError as error:
            st.error(str(error))
            return
        st.session_state["gt_flash"] = (f"{item['name']}: {result['previous_quantity']:g} → {result['new_quantity']:g} "
                                        f"{result['unit']} · now {result['status'].title()}")
        st.rerun()


def _flash() -> None:
    if message := st.session_state.pop("gt_flash", None):
        st.success(message, icon=":material/check_circle:")


def _alerts_panel(alerts: list[dict], key: str) -> None:
    if not alerts:
        st.success("All ingredients are above their reorder points.", icon=":material/verified:")
        return
    for alert in alerts:
        row = st.columns((2.2, 1.6, 1), vertical_alignment="center")
        row[0].markdown(f"**{alert['name']}** {STATUS_BADGE[alert['status']]}")
        row[1].caption(f"{alert['quantity']:g} / {alert['reorder_point']:g} {alert['unit']}")
        if row[2].button("Reorder", key=f"{key}_{alert['ingredient_id']}", icon=":material/add_box:",
                         width="stretch"):
            replenish_dialog(alert)


def render_manager_today() -> None:
    st.caption("Cafeteria manager")
    st.title("Today at a glance")
    _flash()
    data = api.load("/dashboard/manager")
    if data is None:
        return
    row1 = st.columns(5)
    row1[0].metric("Orders today", data["orders_today"], help=f"{data['active_orders']} still in progress")
    row1[1].metric("Order value", money(data["accepted_order_value"]),
                   help=f"Accepted (non-cancelled) order value; average {money(data['average_order_value'])}")
    row1[2].metric("Collected", data["collected_orders"])
    row1[3].metric("Avg rating", "—" if data["average_rating"] is None else f"{data['average_rating']:.1f} / 5")
    row1[4].metric("Healthy meals", _pct(data["healthy_meal_adoption"]),
                   help="Share of today's portions tagged high protein, high fibre, lower sodium or balanced")
    row2 = st.columns(5)
    row2[0].metric("Critical items", data["critical_stock_count"])
    row2[1].metric("Stockouts", data["stockout_count"])
    row2[2].metric("Expected", "—" if data["expected_customers"] is None else data["expected_customers"],
                   help="Expected customers from today's latest forecast; run one in Forecasting")
    row2[3].metric("Customers", data["actual_customers"], help="Distinct employees who ordered today")
    row2[4].metric("Recommended", _pct(data["recommendation_share"]),
                   help="Share of today's portions that were recommended to the employee")

    left, right = st.columns((1.4, 1))
    with left:
        with st.container(border=True):
            st.markdown("#### Top-selling dishes today")
            if data["top_dishes"]:
                st.bar_chart(pd.DataFrame(data["top_dishes"]), x="name", y="portions", horizontal=True, height=240)
            else:
                st.caption("No orders yet today.")
            counts = data["status_counts"]
            st.caption(" · ".join(f"{s.title()} {counts.get(s, 0)}" for s in ORDER_STATUSES))
            st.button("Open live orders", icon=":material/receipt_long:", on_click=go_to, args=("Live orders",))
    with right:
        with st.container(border=True):
            st.markdown("#### Inventory alerts")
            _alerts_panel(data["inventory_alerts"], "today")
    st.caption(f"As of {data['as_of'][:19].replace('T', ' ')} UTC · data: {data['data_state']}")


def _advance(order_id: str, status: str) -> None:
    try:
        api.patch(f"/orders/{order_id}/status", {"status": status})
        st.session_state["gt_flash"] = f"{order_id} → {status}"
    except api.ApiError as error:
        st.session_state["gt_flash_error"] = str(error)


def render_live_orders() -> None:
    st.caption("Service")
    st.title("Live orders")
    _flash()
    if error := st.session_state.pop("gt_flash_error", None):
        st.error(error)
    filters = st.columns((1, 1, 1, 0.6), vertical_alignment="bottom")
    day = filters[0].date_input("Date", value=date.today())
    status = filters[1].selectbox("Status", ["all", *ORDER_STATUSES], format_func=str.title)
    user_id = filters[2].text_input("Employee ID", max_chars=40).strip().upper() or None
    filters[3].button("Refresh", icon=":material/refresh:", width="stretch")
    result = api.load("/orders", date=day.isoformat(), status=None if status == "all" else status, user_id=user_id)
    if result is None:
        return
    orders = result["data"]
    st.caption(f"{len(orders)} order(s)")
    if not orders:
        st.info("No orders match these filters.", icon=":material/info:")
    for order in orders:
        with st.container(border=True):
            row = st.columns((2.2, 1.2, 1, 1, 1.1, 1), vertical_alignment="center")
            row[0].markdown(f"**{order['pickup_reference']}** · {order['order_id']}")
            row[0].caption(", ".join(f"{i['name']} × {i['quantity']}" for i in order["items"]))
            row[1].caption(f"{order['user_id']} · {order['meal_period']} · {order['created_at'][11:16]} UTC")
            row[2].markdown(f"**{money(order['total'])}**")
            row[3].markdown(f"`{order['status']}`")
            if nxt := NEXT_STATUS.get(order["status"]):
                row[4].button(f"Mark {nxt}", key=f"adv_{order['order_id']}", type="primary", width="stretch",
                              on_click=_advance, args=(order["order_id"], nxt))
            if order["status"] in ("confirmed", "preparing"):
                row[5].button("Cancel", key=f"cancel_{order['order_id']}", width="stretch",
                              on_click=_advance, args=(order["order_id"], "cancelled"))


TEMPLATES = {
    "inventory": pd.DataFrame([{"ingredient_id": "ING_PANEER", "name": "Paneer", "quantity": 5000, "unit": "g",
                                "reorder_point": 1500}]),
    "recipes": pd.DataFrame([
        {"dish_id": "DISH_PANEER_BOWL", "dish_name": "Paneer power bowl", "ingredient_id": "ING_PANEER",
         "quantity_per_portion": 120, "price": 150, "diet": "veg", "meal_periods": "lunch|dinner",
         "allergens": "milk", "protein_g": 22, "fibre_g": 6, "sodium_mg": 280, "energy_kcal": 420,
         "catalog_code": "ASC191", "evidence_status": "confirmed"},
        {"dish_id": "DISH_PANEER_BOWL", "dish_name": "Paneer power bowl", "ingredient_id": "ING_RICE",
         "quantity_per_portion": 100},
    ]),
}


def _upload(kind: str, template: pd.DataFrame | None = None) -> None:
    columns = st.columns((2, 1), vertical_alignment="bottom")
    file = columns[0].file_uploader(f"{kind.title()} file (.xlsx or .csv)", type=["xlsx", "csv"], key=f"up_{kind}")
    buffer = io.BytesIO()
    (TEMPLATES[kind] if template is None else template).to_excel(buffer, index=False)
    columns[1].download_button("Template", buffer.getvalue(), f"{kind}_template.xlsx", icon=":material/download:",
                               width="stretch", key=f"tpl_{kind}")
    if not file:
        return
    actions = st.columns(2)
    for mode, label in (("validate", "Validate"), ("commit", "Upload and apply")):
        if actions[0 if mode == "validate" else 1].button(label, key=f"{kind}_{mode}",
                                                          type="primary" if mode == "commit" else "secondary"):
            try:
                result = api.request("POST", f"/upload/{kind}", files={"file": (file.name, file.getvalue())},
                                     data={"mode": mode})
            except api.ApiError as error:
                st.error(str(error))
                return
            if result["errors"]:
                st.error(f"{len(result['errors'])} problem(s) found; nothing was applied.")
                st.dataframe(pd.DataFrame({"error": result["errors"]}), hide_index=True)
            elif mode == "validate":
                st.success("File is valid and ready to apply.")
            else:
                st.success(f"Applied {result['updated']} row group(s).")


def render_inventory() -> None:
    st.caption("Inventory")
    st.title("Ingredient health")
    _flash()
    result = api.load("/inventory")
    if result is None:
        return
    items = result["data"]
    counts = {s: sum(i["status"] == s for i in items) for s in STATUS_BADGE}
    cols = st.columns(3)
    cols[0].metric("Healthy", counts["HEALTHY"])
    cols[1].metric("Critical", counts["CRITICAL"], help="At or below reorder point")
    cols[2].metric("Stockout", counts["STOCKOUT"])
    stock_tab, usage_tab, update_tab, risk_tab = st.tabs(["Stock", "Today's consumption", "Edit stock",
                                                          "Risk & impact"])
    with stock_tab:
        _stock_table(items)
    with usage_tab:
        _consumption_panel()
    with update_tab:
        _update_stock(items)
    with risk_tab:
        _risk_panel()


def _consumption_panel() -> None:
    filters = st.columns((1, 2.4), vertical_alignment="bottom")
    day = filters[0].date_input("Service day", value=date.today(), key="use_day")
    focus = filters[1].text_input("Focus on (semantic search)", key="use_focus", max_chars=100,
                                  placeholder="e.g. dairy, leafy greens, pulses, grains, protein")
    data = api.load("/inventory/consumption", date=day.isoformat(), query=focus.strip() or None)
    if data is None:
        return
    totals = data["totals"]
    cols = st.columns(3)
    cols[0].metric("Orders", totals["orders"], help="All orders for the day, including cancelled")
    cols[1].metric("Portions served", totals["portions"])
    cols[2].metric("Ingredients drawn", totals["ingredients_used"])
    if data["query"]:
        matched = ", ".join(f"{m['name']} ({m['score']:.2f})" for m in data["matched_ingredients"]) or "nothing"
        how = "Qdrant semantic match" if data["semantic_search"] else "Name match (Qdrant unavailable)"
        st.caption(f"{how} for “{data['query']}”: {matched}")
    if not data["ingredients"]:
        st.info("No inventory was drawn by orders for this selection.", icon=":material/info:")
        return
    left, right = st.columns((1.3, 1))
    with left, st.container(border=True):
        st.markdown("#### Most affected ingredients")
        frame = pd.DataFrame(data["ingredients"])
        frame["used"] = frame["used_today"].map("{:g}".format) + " " + frame["unit"]
        frame["left"] = frame["remaining"].map("{:g}".format) + " " + frame["unit"]
        st.dataframe(frame[["name", "used", "orders", "left", "depletion_pct", "status"]], hide_index=True,
                     column_config={"name": "Ingredient", "used": "Used today", "orders": "Orders", "left": "Remaining",
                                    "status": "Status", "depletion_pct": st.column_config.ProgressColumn(
                                        "Share of stock used", min_value=0, max_value=100, format="%.0f%%")})
    with right, st.container(border=True):
        st.markdown("#### Dishes losing headroom")
        if data["affected_dishes"]:
            st.dataframe(pd.DataFrame(data["affected_dishes"])[
                ["name", "portions_before", "portions_now", "lost_pct"]], hide_index=True, column_config={
                "name": "Dish", "portions_before": "Could make (start)", "portions_now": "Can make now",
                "lost_pct": st.column_config.ProgressColumn("Capacity used", min_value=0, max_value=100, format="%.0f%%")})
        else:
            st.caption("No dish lost capacity.")
    with st.container(border=True):
        st.markdown(f"#### What each order drew · {totals['orders_shown']} order(s)")
        st.dataframe(pd.DataFrame([{
            "Time (UTC)": o["time"], "Pickup": o["pickup_reference"], "Employee": o["user_id"], "Status": o["status"],
            "Dishes": ", ".join(o["dishes"]),
            "Ingredients used": ", ".join(f"{i['name']} {i['quantity']:g} {i['unit']}" for i in o["ingredients"]),
        } for o in data["orders"]]), hide_index=True)
        st.caption("Cancelled orders show net zero once their stock is returned.")


def _stock_table(items: list[dict]) -> None:
    view = st.segmented_control("Show", ["All", "Needs attention"], default="All", key="inv_filter") or "All"
    shown = [i for i in items if view == "All" or i["status"] != "HEALTHY"]
    shown.sort(key=lambda i: (i["status"] == "HEALTHY", i["status"] != "STOCKOUT", i["name"]))
    frame = pd.DataFrame([{
        "Ingredient": i["name"], "ID": i["ingredient_id"], "On hand": i["quantity"], "Unit": i["unit"],
        "Reorder point": i["reorder_point"], "Cover": min(i["quantity"] / i["reorder_point"], 3) if i["reorder_point"] else 3,
        "Status": i["status"].title()} for i in shown])
    if frame.empty:
        st.success("Nothing needs attention.", icon=":material/verified:")
        return
    selection = st.dataframe(
        frame, hide_index=True, on_select="rerun", selection_mode="single-row", key="inv_table",
        column_config={"Cover": st.column_config.ProgressColumn("Stock vs reorder point", min_value=0, max_value=3,
                                                                format="%.1fx")})
    rows = selection.selection.rows
    if rows:
        _ingredient_detail(shown[rows[0]])
    else:
        st.caption("Select a row to see affected dishes, history, and replenish.")


def _update_stock(items: list[dict]) -> None:
    with st.container(border=True):
        st.markdown("#### Edit stock in place")
        st.caption("Change on-hand quantity or reorder point, then save. Items at or below their reorder point are "
                   "flagged Critical; zero stock is flagged Stockout. Every change is logged as a stock movement.")
        original = pd.DataFrame([{"ingredient_id": i["ingredient_id"], "name": i["name"], "quantity": i["quantity"],
                                  "unit": i["unit"], "reorder_point": i["reorder_point"],
                                  "status": i["status"].title()} for i in items],
                                columns=["ingredient_id", "name", "quantity", "unit", "reorder_point", "status"])
        if original.empty:
            st.info("No ingredients yet. Add one below or upload an inventory file to start tracking stock.",
                    icon=":material/inventory_2:")
        edited = st.data_editor(
            original, hide_index=True, key="inv_editor", disabled=["ingredient_id", "name", "unit", "status"],
            column_config={"quantity": st.column_config.NumberColumn("On hand", min_value=0.0),
                           "reorder_point": st.column_config.NumberColumn("Reorder point", min_value=0.0),
                           "ingredient_id": "ID", "name": "Ingredient", "unit": "Unit", "status": "Status"})
        changed = edited[(edited["quantity"] != original["quantity"])
                         | (edited["reorder_point"] != original["reorder_point"])]
        if st.button(f"Save {len(changed)} change(s)", type="primary", icon=":material/save:",
                     disabled=changed.empty, key="inv_save"):
            try:
                for row in changed.itertuples():
                    api.patch(f"/inventory/{row.ingredient_id}", {
                        "quantity": float(row.quantity), "reorder_point": float(row.reorder_point),
                        "note": "Edited on dashboard"})
            except api.ApiError as error:
                st.error(str(error))
                return
            st.session_state["gt_flash"] = f"Updated {len(changed)} ingredient(s)"
            st.rerun()
    with st.expander("Upload inventory from Excel", icon=":material/upload_file:"):
        st.caption("Download the template (pre-filled with current stock), edit it in Excel and upload. Columns: "
                   "ingredient_id, name, quantity, unit, reorder_point. The whole file is rejected if any row is invalid.")
        current = pd.DataFrame([{k: i[k] for k in ("ingredient_id", "name", "quantity", "unit", "reorder_point")}
                                for i in items]) if items else None
        _upload("inventory", current)
    with st.expander("Upload recipes", icon=":material/upload_file:"):
        st.caption("One row per dish ingredient. Dish details are read from the first row of each dish. "
                   "Upload inventory first so ingredient IDs exist.")
        _upload("recipes")
    with st.expander("Add one ingredient", icon=":material/add:"):
        with st.form("add_ingredient", border=False):
            row = st.columns(5)
            ingredient_id = row[0].text_input("ID", placeholder="ING_GHEE", max_chars=40)
            name = row[1].text_input("Name", max_chars=80)
            quantity = row[2].number_input("Quantity", min_value=0.0, step=100.0)
            unit = row[3].selectbox("Unit", ["g", "ml", "pcs", "slices", "kg", "l"])
            reorder = row[4].number_input("Reorder point", min_value=0.0, step=100.0)
            if st.form_submit_button("Add ingredient", type="primary"):
                try:
                    api.post("/inventory", {"ingredient_id": ingredient_id.strip(), "name": name.strip(),
                                            "quantity": quantity, "unit": unit, "reorder_point": reorder})
                    st.session_state["gt_flash"] = f"Added {name}"
                    st.rerun()
                except api.ApiError as error:
                    st.error(str(error))


def _risk_panel() -> None:
    risk = api.load("/inventory/risk")
    if risk is None:
        return
    cols = st.columns(3)
    cols[0].metric("Revenue at risk today", money(risk["revenue_at_risk"]),
                   help="Expected portions that current stock cannot cover × dish price")
    cols[1].metric("Dishes at risk", len(risk["dishes_at_risk"]))
    cols[2].metric("Slow movers (waste risk)", len(risk["slow_movers"]))
    with st.container(border=True):
        st.markdown("#### Dishes affected by stock")
        if risk["dishes_at_risk"]:
            frame = pd.DataFrame(risk["dishes_at_risk"])
            frame["swap_suggestions"] = frame["swap_suggestions"].str.join(", ")
            frame["risk"] = frame["risk"].str.replace("_", " ").str.title()
            st.dataframe(frame.drop(columns=["dish_id"]).rename(columns={
                "name": "Dish", "meal_period": "Period", "risk": "Risk", "limiting_ingredient": "Limiting ingredient",
                "portions_possible": "Portions left", "expected_demand": "Expected", "lost_portions": "Short by",
                "revenue_at_risk": "Revenue at risk (₹)", "swap_suggestions": "Suggested swap"}), hide_index=True)
        else:
            st.success("Stock covers expected demand for every dish on today's menu.", icon=":material/verified:")
        st.caption(f"Demand basis: {risk['demand_basis']}. Swaps are in-stock dishes of the same diet, ranked by "
                   "Qdrant semantic similarity when available.")
    with st.container(border=True):
        st.markdown("#### Slow movers: food-waste risk")
        if risk["slow_movers"]:
            st.dataframe(pd.DataFrame(risk["slow_movers"]).drop(columns=["dish_id"]).rename(columns={
                "name": "Dish", "meal_period": "Period", "expected_demand": "Expected", "note": "Action"}),
                hide_index=True)
        else:
            st.caption("No slow movers detected on today's menu.")


def _ingredient_detail(item: dict) -> None:
    with st.container(border=True):
        top = st.columns((3, 1, 1, 1), vertical_alignment="center")
        top[0].markdown(f"#### {item['name']} {STATUS_BADGE[item['status']]}")
        if top[1].button("Replenish", type="primary", icon=":material/add_box:", width="stretch",
                         key="detail_replenish"):
            replenish_dialog(item)
        with top[3].popover("Set stock", width="stretch"):
            amount = st.number_input(f"On hand ({item['unit']})", min_value=0.0, value=float(item["quantity"]),
                                     key="edit_quantity")
            note = st.text_input("Reason", value="Stock count correction", max_chars=200, key="edit_quantity_note")
            if st.button("Save quantity", type="primary", key="save_quantity"):
                try:
                    api.patch(f"/inventory/{item['ingredient_id']}", {"quantity": amount, "note": note})
                    st.session_state["gt_flash"] = f"{item['name']}: {item['quantity']:g} → {amount:g} {item['unit']}"
                    st.rerun()
                except api.ApiError as error:
                    st.error(str(error))
        with top[2].popover("Edit threshold", width="stretch"):
            threshold = st.number_input("Reorder point", min_value=0.0, value=float(item["reorder_point"]),
                                        key="edit_threshold")
            if st.button("Save threshold", type="primary"):
                try:
                    api.patch(f"/inventory/{item['ingredient_id']}", {"reorder_point": threshold})
                    st.session_state["gt_flash"] = f"{item['name']} reorder point set to {threshold:g}"
                    st.rerun()
                except api.ApiError as error:
                    st.error(str(error))
        left, right = st.columns(2)
        affected = api.load(f"/inventory/{item['ingredient_id']}/affected-dishes")
        with left:
            st.markdown("**Affected dishes**")
            if affected and affected["data"]:
                st.dataframe(pd.DataFrame(affected["data"]).rename(columns={
                    "name": "Dish", "quantity_per_portion": f"Per portion ({item['unit']})",
                    "portions_possible": "Portions possible"}).drop(columns=["dish_id"]), hide_index=True)
            else:
                st.caption("No recipes use this ingredient.")
        movements = api.load(f"/inventory/{item['ingredient_id']}/movements", limit=20)
        with right:
            st.markdown("**Recent movements**")
            if movements and movements["data"]:
                frame = pd.DataFrame(movements["data"])
                frame["when"] = frame["created_at"].str[:16].str.replace("T", " ")
                st.dataframe(frame[["when", "type", "quantity", "user_id"]], hide_index=True)
            else:
                st.caption("No movements recorded yet.")


RECIPE_PAGE = 20


@st.fragment(run_every=10)
def _catalog_panel() -> None:
    status = api.load("/catalog/status")
    if status is None:
        return
    with st.container(border=True):
        cols = st.columns((3, 1), vertical_alignment="center")
        cols[0].markdown(f"#### Food catalog · {status['recipes']} recipes · {status['on_menu']} on the menu")
        state = "syncing…" if status["running"] else "sync failed" if status.get("error") else "up to date"
        synced = (status.get("synced_at") or "never")[:16].replace("T", " ")
        cols[0].caption(f"Source: Qdrant `food_nutrients` · last sync {synced} UTC · {state} · "
                        f"{status['images']} dishes with a verified photo (others show a placeholder)")
        if cols[1].button("Sync from Qdrant", icon=":material/sync:", width="stretch", disabled=status["running"]):
            try:
                api.post("/catalog/sync")
            except api.ApiError as error:
                st.error(str(error))
        if status.get("error"):
            st.error(f"Last sync failed: {status['error']}", icon=":material/error:")
        st.caption("New and updated dishes arrive automatically; your menu choices, prices and meal periods are never overwritten.")


def _save_recipes(updates: list[dict]) -> None:
    try:
        api.patch("/recipes", {"updates": updates})
    except api.ApiError as error:
        st.error(str(error))
        return
    api.recommendations.clear()
    api.menu_page.clear()
    st.session_state["mm_version"] = st.session_state.get("mm_version", 0) + 1  # Resets the editor's pending edits.
    st.session_state["gt_flash"] = f"Saved changes to {len(updates)} recipe(s)"
    st.rerun()


def _bulk(on_menu: bool, query: str, period: str | None) -> None:
    try:
        result = api.post("/recipes/bulk-menu", {"on_menu": on_menu, "q": query, "meal_period": period})
    except api.ApiError as error:
        st.error(str(error))
        return
    api.recommendations.clear()
    api.menu_page.clear()
    st.session_state["mm_version"] = st.session_state.get("mm_version", 0) + 1
    st.session_state["gt_flash"] = f"{'Added' if on_menu else 'Excluded'} {result['updated']} recipe(s)"
    st.rerun()


def _changes(before: pd.DataFrame, after: pd.DataFrame) -> list[dict]:
    updates = []
    for old, new in zip(before.to_dict("records"), after.to_dict("records")):
        change: dict = {}
        if new["On menu"] != old["On menu"]:
            change["on_menu"] = bool(new["On menu"])
        if pd.notna(new["Price"]) and new["Price"] != old["Price"]:
            change["price"] = float(new["Price"])
        periods = [p for p in MEAL_PERIODS if new[p.title()]]
        if periods != [p for p in MEAL_PERIODS if old[p.title()]] and periods:
            change["meal_periods"] = periods
        if change:
            updates.append({"dish_id": old["dish_id"], **change})
    return updates


def render_menu_management() -> None:
    st.caption("Menu")
    st.title("Menu management")
    _flash()
    _catalog_panel()
    filters = st.columns((2.4, 1.2, 1.6), vertical_alignment="bottom")
    query = filters[0].text_input("Search recipes", max_chars=80, placeholder="e.g. paneer, soup, cake",
                                  icon=":material/search:").strip()
    period = filters[1].selectbox("Meal period", ["All", *MEAL_PERIODS], format_func=str.title)
    show = filters[2].segmented_control("Show", ["All", "On menu", "Excluded"], default="All", key="mm_show") or "All"
    period_filter = None if period == "All" else period
    page_key = f"mm_page_{query}_{period}_{show}"
    page = st.session_state.get(page_key, 0)
    data = api.load("/recipes", q=query or None, meal_period=period_filter, on_menu={"On menu": True, "Excluded": False}.get(show),
                    limit=RECIPE_PAGE, offset=page * RECIPE_PAGE)
    if data is None:
        return
    if not data["data"]:
        st.info("No recipes found. A new database fills itself from the Qdrant catalog; use Sync if it is still empty.",
                icon=":material/info:")
        return

    head = st.columns((3, 1.2), vertical_alignment="center")
    head[0].markdown(f"#### {data['total']} recipe(s)")
    with head[1].popover("Bulk actions", icon=":material/library_add_check:", width="stretch"):
        st.caption(f"Applies to all {data['total']} recipes matching the current search and meal period.")
        if st.button("Add all to menu", icon=":material/playlist_add:", width="stretch"):
            _bulk(True, query, period_filter)
        if st.button("Exclude all from menu", icon=":material/playlist_remove:", width="stretch"):
            _bulk(False, query, period_filter)

    before = pd.DataFrame([{
        "dish_id": r["dish_id"], "On menu": r["on_menu"], "Dish": r["name"], "Diet": r["diet"].replace("_", "-"),
        "Price": float(r["price"]), **{p.title(): p in r["meal_periods"] for p in MEAL_PERIODS},
        "Stock": "tracked" if r["stock_tracked"] else "not tracked"} for r in data["data"]])
    after = st.data_editor(
        before, hide_index=True, key=f"mm_editor_{page_key}_{st.session_state.get('mm_version', 0)}", disabled=["dish_id", "Dish", "Diet", "Stock"],
        column_config={"dish_id": None, "Price": st.column_config.NumberColumn("Price (₹)", min_value=1, max_value=5000, step=5),
                       "On menu": st.column_config.CheckboxColumn("On menu"),
                       "Stock": st.column_config.TextColumn("Stock", help="Only dishes with ingredient lines (recipe upload) use inventory")})
    updates = _changes(before, after)
    actions = st.columns((1.4, 1, 1, 3), vertical_alignment="center")
    if actions[0].button(f"Save {len(updates)} change(s)", type="primary", icon=":material/save:", disabled=not updates,
                         key="mm_save", width="stretch"):
        _save_recipes(updates)
    last_page = max(0, (data["total"] - 1) // RECIPE_PAGE)
    actions[1].button("Previous", icon=":material/chevron_left:", disabled=page == 0, key="mm_prev", width="stretch",
                      on_click=_turn_page, args=(page_key, -1))
    actions[2].button("Next", icon=":material/chevron_right:", disabled=page >= last_page, key="mm_next", width="stretch",
                      on_click=_turn_page, args=(page_key, 1))
    actions[3].caption(f"Page {page + 1} of {last_page + 1} · unsaved edits on a page are lost when you change page")


def _turn_page(key: str, step: int) -> None:
    st.session_state[key] = max(0, st.session_state.get(key, 0) + step)


def _model_panel() -> None:
    status = api.load("/forecast/model")
    if status is None:
        return
    with st.container(border=True):
        top = st.columns((3, 1), vertical_alignment="center")
        top[0].markdown("#### Prediction models")
        if top[1].button("Retrain models", icon=":material/model_training:", width="stretch", key="retrain"):
            try:
                with st.spinner("Training on order history…"):
                    status = api.post("/forecast/model/train")
                st.session_state.pop("gt_forecast", None)
                st.toast("Models retrained", icon=":material/check_circle:")
            except api.ApiError as error:
                st.warning(str(error), icon=":material/info:")
        meta = status["metadata"]
        if not meta:
            st.caption("No trained models yet. Forecasts use the same-weekday baseline. Retrain once order history exists.")
            return
        cols = st.columns(2)
        for col, (name, label, unit) in zip(cols, (("customer_demand", "Customer demand", "customers"),
                                                     ("dish_demand", "Dish demand", "portions"))):
            m = meta[name]
            active = name in status["active_models"]
            col.metric(f"{label} · MAE", f"{m['mae']:.3f} {unit}",
                       f"{m['mae'] - m['baseline_mae']:+.3f} vs baseline", delta_color="inverse",
                       help=f"WAPE {m['wape']}% (baseline {m['baseline_wape']}%) on {m['test_rows']} held-out rows "
                            f"from {m['test_from']}")
            col.caption(":green-badge[In use]" if active else ":orange-badge[Baseline in use — model did not beat it]")
        demo = f" · :orange[{meta['demo_order_share']:.0f}% demo orders]" if meta["demo_order_share"] else ""
        st.caption(f"{meta['model_version']} · trained {meta['trained_at'][:16].replace('T', ' ')} UTC on "
                   f"{meta['orders_used']} orders ({meta['history_from']} → {meta['history_to']}){demo}")


def render_forecasting() -> None:
    st.caption("Forecasting")
    st.title("Demand and preparation planning")
    _model_panel()
    with st.form("forecast", border=True):
        cols = st.columns(3)
        target = cols[0].date_input("Forecast date", value=date.today() + timedelta(days=1))
        period = cols[1].selectbox("Meal period", ["all", *MEAL_PERIODS], format_func=str.title)
        buffer = cols[2].slider("Preparation buffer %", 0, 30, 5)
        run = st.form_submit_button("Run forecast", type="primary", icon=":material/insights:")
    if run:
        try:
            st.session_state["gt_forecast"] = api.post("/forecast/run", {
                "date": target.isoformat(), "meal_period": None if period == "all" else period,
                "buffer_percent": buffer})
        except api.ApiError as error:
            st.error(str(error))
    forecast = st.session_state.get("gt_forecast")
    if forecast is None:
        try:
            forecast = api.get("/forecast/latest")
        except api.ApiError:
            st.info("Run a forecast to plan preparation and spot ingredient shortfalls.", icon=":material/info:")
            return
    st.markdown(f"#### Forecast for {forecast['date']} · {(forecast['meal_period'] or 'all periods').title()}")
    st.caption(f"Method: {forecast['method'].replace('_', ' ')} · {forecast['note']}")
    cols = st.columns(4)
    cols[0].metric("Expected customers", forecast["expected_customers"])
    cols[1].metric("Projected order value", money(forecast["projected_order_value"]))
    cols[2].metric("Ingredient shortfalls", len(forecast["shortfalls"]))
    cols[3].metric("History days used", forecast["history_days_used"])
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**Expected dish orders and preparation**")
            st.dataframe(pd.DataFrame(forecast["dishes"]).rename(columns={
                "name": "Dish", "meal_period": "Period", "expected_orders": "Expected",
                "recommended_preparation": "Prepare", "projected_order_value": "Value (₹)"}).drop(columns=["dish_id"]),
                hide_index=True)
    with right:
        with st.container(border=True):
            st.markdown("**Ingredient requirements**")
            frame = pd.DataFrame(forecast["ingredients"])
            if not frame.empty:
                st.dataframe(frame.rename(columns={"name": "Ingredient", "required": "Required", "on_hand": "On hand",
                                                   "shortfall": "Shortfall", "unit": "Unit"})
                             .drop(columns=["ingredient_id"]), hide_index=True)
            if forecast["shortfalls"]:
                st.warning("Replenish before service: " + ", ".join(
                    f"{s['name']} ({s['shortfall']:g} {s['unit']})" for s in forecast["shortfalls"]),
                    icon=":material/warning:")


def render_executive() -> None:
    st.caption("Executive analytics")
    st.title("Cafeteria performance, connected")
    days = st.segmented_control("Period", [7, 30, 90], default=30, format_func=lambda d: f"Last {d} days",
                                key="exec_days") or 30
    data = api.load("/dashboard/executive", days=days)
    if data is None:
        return
    customer, ops, inventory, financial = data["customer"], data["operations"], data["inventory"], data["financial"]
    sections = [
        ("Customer", [("Average rating", "—" if customer["average_rating"] is None else f"{customer['average_rating']:.1f} / 5"),
                      ("Repeat-order rate", _pct(customer["repeat_order_rate"])),
                      ("Recommended share", _pct(customer["recommendation_share"])),
                      ("Healthy-meal adoption", _pct(customer["healthy_meal_adoption"]))]),
        ("Operations", [("Orders", ops["orders"]), ("Fulfilment rate", _pct(ops["fulfilment_rate"])),
                        ("Avg completion", "—" if ops["average_completion_minutes"] is None
                         else f"{ops['average_completion_minutes']:.0f} min"),
                        ("Cancelled", ops["cancelled_orders"])]),
        ("Inventory", [("Critical", inventory["critical_stock_count"]), ("Stockouts", inventory["stockout_count"]),
                       ("Replenishments", inventory["replenishments"]), ("Customers", customer["customers"])]),
        ("Financial", [("Accepted order value", money(financial["accepted_order_value"])),
                       ("Collected order value", money(financial["collected_order_value"])),
                       ("Average order value", money(financial["average_order_value"])),
                       ("Ratings received", customer["ratings_count"])]),
    ]
    for title, metrics in sections:
        st.markdown(f"##### {title}")
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metrics):
            col.metric(label, value)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**Monthly healthy-meal adoption and orders**")
            trend = pd.DataFrame(data["monthly_trend"])
            st.line_chart(trend, x="month", y="healthy_meal_adoption", height=220)
            st.bar_chart(trend, x="month", y="orders", height=160)
    with right:
        with st.container(border=True):
            st.markdown("**Forecast vs actual customers**")
            if ops["forecast_vs_actual"]:
                st.bar_chart(pd.DataFrame(ops["forecast_vs_actual"]), x="date", y=["expected", "actual"],
                             stack=False, height=220)
            else:
                st.caption("Run forecasts for past or current dates to compare with actuals.")
            st.markdown("**Top ingredient consumption**")
            if inventory["top_consumption"]:
                st.dataframe(pd.DataFrame(inventory["top_consumption"]), hide_index=True)
            else:
                st.caption("No consumption recorded in this period.")
    st.caption(f"{data['from']} to {data['to']}. Values are order values from demo payments, not audited revenue.")


def _ask(question: str) -> None:
    try:
        answer = api.post("/copilot", {"question": question})
    except api.ApiError as error:
        answer = {"answer": f"Sorry, I couldn't answer: {error}", "evidence": [], "intent": "error"}
    st.session_state["gt_copilot_history"].append({"question": question, **answer})


def render_copilot() -> None:
    st.caption("Read-only copilot")
    st.title("Ask the cafeteria anything")
    st.caption("Answers come from live orders, inventory, forecasts and feedback. The copilot never changes data.")
    suggestions = api.load("/copilot/suggestions")
    if suggestions:
        with st.container(horizontal=True):
            for prompt in suggestions["suggestions"]:
                st.button(prompt, key=f"prompt_{prompt}", on_click=_ask, args=(prompt,))
    for turn in st.session_state["gt_copilot_history"]:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            st.write(turn["answer"])
            for line in turn["evidence"]:
                st.caption(f"• {line}")
            if turn.get("source"):
                st.caption("Answered by the LLM from live data" if turn["source"] == "llm" else "Rule-based answer from live data")
    if question := st.chat_input("Ask about stock, sales, demand, wellness trends…"):
        _ask(question)
        st.rerun()
