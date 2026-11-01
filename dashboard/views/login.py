"""Login: user ID only. Unknown IDs become employees; manager IDs must already exist."""

from __future__ import annotations

import re
import time

import streamlit as st

from dashboard import api
from dashboard.state import sign_in, sign_out

COOKIE = "ecos_session"
REFRESH_SECONDS = 60


def _check(token: str) -> dict | None:
    try:
        return api.request("GET", "/auth/session", headers={"X-Session-Token": token})
    except api.ApiError:
        return None


def restore_session() -> None:
    """After a browser reload, sign the user back in from the session cookie and reopen the same page."""
    token = st.context.cookies.get(COOKIE)
    # Cookies are read once per browser connection, so skip a token already rejected or revoked.
    if not isinstance(token, str) or not token or token == st.session_state.get("gt_cookie_rejected"):
        return
    profile = _check(token)
    if profile is None:
        st.session_state["gt_cookie_rejected"] = token
        st.session_state["gt_cookie"] = ("", 0)
        return
    sign_in({**profile, "session_token": token}, st.query_params.get("view"))


def keep_alive() -> None:
    """While the user is active, slide the 30-minute session (server and cookie); sign out once it has expired."""
    token = st.session_state.get("gt_session")
    if not token or time.time() - st.session_state.get("gt_session_checked", 0) < REFRESH_SECONDS:
        return
    profile = _check(token)
    if profile is None:
        sign_out()
        st.session_state["gt_cookie_rejected"] = token
        st.session_state["gt_expired"] = True
        st.rerun()
    st.session_state["gt_session_checked"] = time.time()
    st.session_state["gt_cookie"] = (token, profile["session_minutes"] * 60)


def write_cookie() -> None:
    """Apply a pending cookie change in the browser (max-age 0 deletes it)."""
    pending = st.session_state.pop("gt_cookie", None)
    if pending is None:
        return
    token, max_age = pending
    if not re.fullmatch(r"[A-Za-z0-9_-]*", token):
        return
    st.html(f"<script>document.cookie = '{COOKIE}={token}; Max-Age={int(max_age)}; Path=/; SameSite=Strict';</script>",
            unsafe_allow_javascript=True)


def render_login() -> None:
    _, center, _ = st.columns((1, 1.3, 1))
    with center:
        st.markdown('<div class="gt-kicker">Enterprise Cafeteria Operating System</div>', unsafe_allow_html=True)
        st.title("🥙 Welcome to ECOS")
        st.caption("Good food. Smarter operations. Healthier people.")
        if st.session_state.pop("gt_expired", False):
            st.info("Your session expired after 30 minutes of inactivity. Please log in again.", icon=":material/timer_off:")
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
