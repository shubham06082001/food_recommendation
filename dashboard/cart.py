"""Cart panel and demo-payment checkout (employees only). The cart stays in session until checkout."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.state import change_quantity, go_to, remove_from_cart, toggle_cart


def _checkout() -> None:
    cart = st.session_state["gt_cart"]
    payload = {"items": [{"dish_id": d, "quantity": line["quantity"]} for d, line in cart.items()],
               "recommended_dish_ids": [d for d, line in cart.items() if line.get("recommended")]}
    try:
        order = api.post("/orders", payload)
    except api.ApiError as error:
        st.session_state["gt_checkout_error"] = str(error)
        return
    st.session_state["gt_cart"] = {}
    st.session_state["gt_cart_open"] = False
    # Stock changed, so recommendations may list dishes that are no longer available.
    api.recommendations.clear()
    st.session_state["gt_last_order"] = order
    st.session_state.pop("gt_checkout_error", None)
    go_to("My orders")


def render_cart_panel() -> None:
    if st.session_state["role"] != "employee" or not st.session_state["gt_cart_open"]:
        return
    with st.sidebar, st.container(key="gt_cart"):
        header = st.columns((2, 1.3), vertical_alignment="center")
        header[0].markdown("#### Your cart")
        header[1].button("Close", key="gt_cart_close", icon=":material/close:", on_click=toggle_cart)
        cart = st.session_state["gt_cart"]
        if not cart:
            st.caption("Your cart is empty. Add a meal from the menu.")
            return
        total = 0
        for dish_id, line in cart.items():
            line_total = line["price"] * line["quantity"]
            total += line_total
            st.markdown(f"**{line['name']}** · ₹{line_total:,.0f}")
            stepper = st.columns((1, 1, 1, 2.2), vertical_alignment="center")
            stepper[0].button("−", key=f"minus_{dish_id}", on_click=change_quantity, args=(dish_id, -1))
            stepper[1].markdown(f"<div class='gt-qty'>{line['quantity']}</div>", unsafe_allow_html=True)
            stepper[2].button("+", key=f"plus_{dish_id}", on_click=change_quantity, args=(dish_id, 1))
            stepper[3].button("Remove", key=f"remove_{dish_id}", on_click=remove_from_cart, args=(dish_id,))
        st.markdown(f"<div class='gt-cart-total'><span>Total</span><b>₹{total:,.0f}</b></div>", unsafe_allow_html=True)
        if error := st.session_state.get("gt_checkout_error"):
            st.error(error, icon=":material/error:")
        st.button("Place order – demo payment", type="primary", width="stretch", on_click=_checkout,
                  icon=":material/check_circle:")
        st.caption("No payment is taken. Orders are marked as demo-paid.")
