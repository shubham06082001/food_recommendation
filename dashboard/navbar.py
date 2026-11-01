"""Top bar: brand kicker, date and connection pill (cart and profile live in the sidebar)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from dashboard.utils import pill


def render_topbar() -> None:
    left, right = st.columns((1.4, 1), vertical_alignment="center")
    left.markdown('<div class="gt-kicker">Cafeteria intelligence</div>', unsafe_allow_html=True)
    with right.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
        st.caption(date.today().strftime("%A, %d %B %Y"))
        st.markdown(pill("Live data"), unsafe_allow_html=True)
