"""Employee profile and preferences, saved to MongoDB through the API."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.config import ALLERGEN_OPTIONS, DIET_OPTIONS, DISCLAIMER, TAG_LABELS
from dashboard.state import go_to

CATEGORIES = ["indian", "south indian", "breakfast", "snacks", "rice bowls", "curries"]


def render_profile() -> None:
    st.caption("Settings")
    st.title("Profile and preferences")
    user = api.load(f"/users/{st.session_state['user_id']}")
    if user is None:
        return
    prefs = user.get("preferences") or {}
    if not user.get("profile_complete"):
        st.info("Tell us how you like to eat so we can recommend the right meals.", icon=":material/waving_hand:")
    known_allergens = sorted(set(ALLERGEN_OPTIONS) | set(prefs.get("declared_allergens", [])))
    with st.form("preferences", border=True):
        name = st.text_input("Name", value=user.get("name", ""), max_chars=80)
        diet = st.selectbox("Dietary preference", list(DIET_OPTIONS), format_func=DIET_OPTIONS.get,
                            index=list(DIET_OPTIONS).index(prefs.get("dietary_preference", "no_preference")))
        goals = st.pills("Wellness goals", list(TAG_LABELS), format_func=TAG_LABELS.get, selection_mode="multi",
                         default=prefs.get("wellness_goals", []))
        allergens = st.multiselect("Declared allergen exclusions", known_allergens,
                                   default=prefs.get("declared_allergens", []), format_func=str.title)
        favourites = st.multiselect("Favourite categories", CATEGORIES, format_func=str.title,
                                    default=[f for f in prefs.get("favourite_categories", []) if f in CATEGORIES])
        consent = st.checkbox("I consent to ECOS using these preferences to personalise recommendations and my "
                              "wellness scorecard.", value=bool(prefs.get("consented")))
        submitted = st.form_submit_button("Save preferences", type="primary", icon=":material/save:")
    st.caption(DISCLAIMER)
    if not submitted:
        return
    if not consent:
        st.warning("Please give consent to save your preferences.", icon=":material/policy:")
        return
    try:
        api.put(f"/users/{st.session_state['user_id']}/preferences", {
            "name": name.strip() or None, "dietary_preference": diet, "wellness_goals": goals or [],
            "declared_allergens": allergens, "favourite_categories": favourites, "consented": True})
    except api.ApiError as error:
        st.error(str(error), icon=":material/error:")
        return
    if name.strip():
        st.session_state["user_name"] = name.strip()
    api.recommendations.clear()
    api.meal_plan.clear()
    st.success("Preferences saved. Your recommendations are now personalised.", icon=":material/check_circle:")
    st.button("See my recommendations", type="primary", on_click=go_to, args=("Menu",))