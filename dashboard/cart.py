"""Cart panel and demo-payment checkout (employees only). The cart stays in session until checkout."""

from __future__ import annotations

import html
from uuid import uuid4

import streamlit as st

from dashboard import api
from dashboard.state import change_quantity, go_to, remove_from_cart, toggle_cart


def _checkout() -> None:
    cart = st.session_state["gt_cart"]
    # The same id is resent on retries, so a double click or timeout never creates two orders.
    request_id = st.session_state.setdefault("gt_request_id", uuid4().hex)
    payload = {"items": [{"dish_id": d, "quantity": line["quantity"]} for d, line in cart.items()],
               "recommended_dish_ids": [d for d, line in cart.items() if line.get("recommended")],
               "client_request_id": request_id}
    try:
        order = api.post("/orders", payload)
    except api.ApiError as error:
        st.session_state["gt_checkout_error"] = str(error)
        return
    st.session_state.pop("gt_request_id", None)
    st.session_state["gt_cart"] = {}
    st.session_state["gt_cart_open"] = False
    # Stock changed, so recommendations may list dishes that are no longer available.
    api.recommendations.clear()
    api.meal_plan.clear()
    st.session_state["gt_last_order"] = order
    st.session_state.pop("gt_checkout_error", None)
    go_to("My orders")


def render_cart_panel() -> None:
    """Rendered inside the sidebar, directly under the Cart entry."""
    if st.session_state["role"] != "employee" or not st.session_state["gt_cart_open"]:
        return
    with st.container(key="gt_cart_panel"):
        header = st.columns((4, 1), vertical_alignment="center")
        header[0].markdown('<p class="gt-kicker">Order</p><h4 class="gt-cart-title">Your cart</h4>', unsafe_allow_html=True)
        header[1].button(":material/close:", key="gt_cart_close", help="Close cart", on_click=toggle_cart)
        cart = st.session_state["gt_cart"]
        if not cart:
            st.caption("Your cart is empty. Add a meal to get started.")
            return
        total = 0
        for dish_id, line in cart.items():
            line_total = line["price"] * line["quantity"]
            total += line_total
            st.markdown(f"<div class='gt-cart-line'><span>{html.escape(line['name'])}</span>"
                        f"<b>₹{line_total:,.0f}</b></div>", unsafe_allow_html=True)
            stepper = st.columns((1, 1, 1, 1), vertical_alignment="center")
            stepper[0].button(":material/remove:", key=f"minus_{dish_id}", help="One less",
                              on_click=change_quantity, args=(dish_id, -1))
            stepper[1].markdown(f"<div class='gt-qty'>{line['quantity']}</div>", unsafe_allow_html=True)
            stepper[2].button(":material/add:", key=f"plus_{dish_id}", help="One more",
                              on_click=change_quantity, args=(dish_id, 1))
            stepper[3].button(":material/delete:", key=f"remove_{dish_id}", help="Remove",
                              on_click=remove_from_cart, args=(dish_id,))
        st.markdown(f"<div class='gt-cart-total'><span>Total</span><b>₹{total:,.0f}</b></div>", unsafe_allow_html=True)
        if error := st.session_state.get("gt_checkout_error"):
            st.error(error, icon=":material/error:")
        st.button("Place order", type="primary", width="stretch", on_click=_checkout, key="gt_place_order",
                  icon=":material/check_circle:")
        st.caption("Demo payment: no money is taken.")
