"""Left navigation rail: signed-in user on top, role navigation, the cart (employees), and sign out."""

from __future__ import annotations

import html

import streamlit as st

from dashboard.cart import render_cart_panel
from dashboard.config import ROLE_NAV
from dashboard.state import go_to, sign_out, toggle_cart


def render_sidebar() -> None:
    role = st.session_state["role"]
    view = st.session_state["gt_view"]
    with st.sidebar:
        name = html.escape(st.session_state["user_name"] or st.session_state["user_id"])
        st.html(f'<div class="gt-user"><span class="gt-avatar">{name[:1].upper()}</span>'
                f'<div><b>{name}</b><br><small>{html.escape(st.session_state["user_id"])} · {role.title()} · ECOS</small>'
                f'</div></div>')
        for item, icon in ROLE_NAV[role]:
            st.button(item, key=f"nav_{item}", icon=icon, width="stretch",
                      type="primary" if item == view else "secondary", on_click=go_to, args=(item,))
        if role == "employee":
            cart = st.session_state["gt_cart"]
            count = sum(line["quantity"] for line in cart.values())
            total = sum(line["quantity"] * line["price"] for line in cart.values())
            label = f"Cart · {count} item{'s' * (count != 1)}" + (f" · ₹{total:,.0f}" if count else "")
            st.button(label, key="nav_cart", icon=":material/shopping_bag:", width="stretch",
                      type="primary" if st.session_state["gt_cart_open"] else "secondary", on_click=toggle_cart)
            render_cart_panel()
        st.button("Sign out", key="sign_out", icon=":material/logout:", width="stretch", on_click=sign_out)
