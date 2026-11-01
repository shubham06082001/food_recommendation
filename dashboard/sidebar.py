"""Left navigation rail: brand, role-specific navigation, signed-in user, and sign out."""

from __future__ import annotations

import html

import streamlit as st

from dashboard.config import ROLE_NAV
from dashboard.state import go_to, sign_out


def render_sidebar() -> None:
    role = st.session_state["role"]
    view = st.session_state["gt_view"]
    with st.sidebar:
        st.markdown("### 🥙 ECOS")
        st.caption("Enterprise Cafeteria Operating System")
        st.caption("Manager workspace" if role == "manager" else "Employee workspace")
        for item, icon in ROLE_NAV[role]:
            st.button(item, key=f"nav_{item}", icon=icon, width="stretch",
                      type="primary" if item == view else "secondary", on_click=go_to, args=(item,))
        st.divider()
        name = html.escape(st.session_state["user_name"] or st.session_state["user_id"])
        st.html(f'<div class="gt-user"><span class="gt-avatar">{name[:1].upper()}</span>'
                f'<div><b>{name}</b><br><small>{html.escape(st.session_state["user_id"])} · {role.title()}</small></div></div>')
        st.button("Sign out", key="sign_out", icon=":material/logout:", width="stretch", on_click=sign_out)
