"""Top bar: brand kicker, date, connection pill, cart toggle (employees), and settings."""

from __future__ import annotations

from datetime import date

import streamlit as st

from dashboard.state import go_to, toggle_cart
from dashboard.utils import pill


def render_topbar() -> None:
    left, right = st.columns((1.4, 1), vertical_alignment="center")
    left.markdown('<div class="gt-kicker">Cafeteria intelligence</div>', unsafe_allow_html=True)
    with right.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
        st.caption(date.today().strftime("%A, %d %B %Y"))
        st.markdown(pill("Live data"), unsafe_allow_html=True)
        if st.session_state["role"] == "employee":
            count = sum(line["quantity"] for line in st.session_state["gt_cart"].values())
            st.button(f"Cart ({count})", key="gt_cart_btn", icon=":material/shopping_bag:", on_click=toggle_cart)
            st.button("Settings", key="gt_settings_btn", icon=":material/settings:", on_click=go_to, args=("Profile",))
