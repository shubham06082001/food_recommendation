"""Entry point: run with `streamlit run dashboard/app.py` (or the root-level canva_clone.py)."""

from __future__ import annotations

import sys
from pathlib import Path

# streamlit run adds this file's own directory to sys.path, not the project root; add the
# root explicitly so the absolute `dashboard.*` imports below resolve regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard import api
from dashboard.cart import render_cart_panel
from dashboard.navbar import render_topbar
from dashboard.sidebar import render_sidebar
from dashboard.state import initialize_state
from dashboard.theme import apply_canva_theme
from dashboard.views import render_view
from dashboard.views.login import render_login, restore_session


@st.fragment(run_every=5)
def _wait_for_backend() -> None:
    """Rendered only while the API is down; on reconnect a full rerun removes the banner."""
    if api.is_backend_up():
        st.rerun()
    st.error(f"Backend not connected ({api.API_URL}). Retrying every 5 seconds…", icon=":material/cloud_off:")


def render_connection_banner() -> None:
    # Auto-refresh only while disconnected so it never interrupts forms in normal use.
    if not api.is_backend_up():
        _wait_for_backend()


def main() -> None:
    """Run the ECOS dashboard: login gate, then the role workspace."""
    st.set_page_config(page_title="ECOS", page_icon="\U0001F959", layout="wide")
    initialize_state()
    apply_canva_theme()
    render_connection_banner()
    if not st.session_state["user_id"]:
        restore_session()
    if not st.session_state["user_id"]:
        render_login()
        return
    render_sidebar()
    render_cart_panel()
    render_topbar()
    render_view()


if __name__ == "__main__":
    main()
