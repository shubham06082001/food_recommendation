"""Routes the signed-in role and current view to its rendering function."""

from __future__ import annotations

import streamlit as st

from dashboard.config import ROLE_LANDING
from dashboard.views.employee import render_employee_home, render_menu, render_my_orders, render_wellness
from dashboard.views.manager import (render_copilot, render_executive, render_forecasting, render_inventory,
                                     render_live_orders, render_manager_today, render_menu_management)
from dashboard.views.profile import render_profile

__all__ = ["render_view"]

_RENDERERS = {
    "employee": {
        "Home": render_employee_home, "Menu": render_menu, "My orders": render_my_orders,
        "My wellness": render_wellness, "Profile": render_profile,
    },
    "manager": {
        "Today": render_manager_today, "Live orders": render_live_orders, "Inventory": render_inventory,
        "Menu management": render_menu_management, "Forecasting": render_forecasting,
        "Executive": render_executive, "Copilot": render_copilot,
    },
}


def render_view() -> None:
    """Render the current view; a role can only reach its own pages."""
    role = st.session_state["role"]
    pages = _RENDERERS[role]
    view = st.session_state["gt_view"]
    if view not in pages:
        view = st.session_state["gt_view"] = ROLE_LANDING[role]
    pages[view]()
