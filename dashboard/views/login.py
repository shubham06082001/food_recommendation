"""Login: user ID only. Unknown IDs become employees; manager IDs must already exist."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.state import sign_in


def restore_session() -> None:
    """After a browser reload, sign the user back in from the URL and reopen the same page."""
    user_id = st.query_params.get("user")
    if not user_id:
        return
    try:
        sign_in(api.post("/auth/login", {"user_id": user_id}), st.query_params.get("view"))
    except api.ApiError:
        st.query_params.clear()


def render_login() -> None:
    _, center, _ = st.columns((1, 1.3, 1))
    with center:
        st.markdown('<div class="gt-kicker">Enterprise Cafeteria Operating System</div>', unsafe_allow_html=True)
        st.title("🥙 Welcome to ECOS")
        st.caption("Good food. Smarter operations. Healthier people.")
        with st.form("login", border=True):
            user_id = st.text_input("User ID", placeholder="e.g. EMP001 or MGR001", max_chars=40)
            submitted = st.form_submit_button("Log in", type="primary", width="stretch", icon=":material/login:")
        st.caption("New ID? An employee account is created automatically. Manager IDs are provisioned by admin "
                   "(demo manager: **MGR001**).")
        if submitted:
            if not user_id.strip():
                st.warning("Enter your user ID.", icon=":material/badge:")
                return
            try:
                profile = api.post("/auth/login", {"user_id": user_id.strip()})
            except api.ApiError as error:
                st.error(str(error), icon=":material/error:")
                return
            sign_in(profile)
            st.rerun()
