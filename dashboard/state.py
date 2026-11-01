"""Session state: login identity, navigation, and the pre-checkout cart. All business data lives in the API."""

from __future__ import annotations

import time

import streamlit as st

from dashboard import api
from dashboard.config import ROLE_LANDING


def initialize_state() -> None:
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("gt_view", None)
    # cart: dish_id -> {"name", "price", "quantity", "recommended"}
    st.session_state.setdefault("gt_cart", {})
    st.session_state.setdefault("gt_cart_open", False)
    st.session_state.setdefault("gt_copilot_history", [])


def sign_in(profile: dict, view: str | None = None) -> None:
    st.session_state["user_id"] = profile["user_id"]
    st.session_state["role"] = profile["role"]
    st.session_state["user_name"] = profile["name"]
    st.session_state["gt_view"] = ROLE_LANDING[profile["role"]]
    if profile["role"] == "employee" and not profile["profile_complete"]:
        st.session_state["gt_view"] = "Profile"
    if view:
        st.session_state["gt_view"] = view
    if token := profile.get("session_token"):
        st.session_state["gt_session"] = token
        st.session_state["gt_cookie"] = (token, profile["session_minutes"] * 60)
    st.session_state["gt_session_checked"] = time.time()
    # Only the page lives in the URL; identity is restored from the session cookie.
    st.query_params.pop("user", None)
    st.query_params["view"] = st.session_state["gt_view"]


def sign_out() -> None:
    if token := st.session_state.get("gt_session"):
        try:
            api.request("POST", "/auth/logout", headers={"X-Session-Token": token})
        except api.ApiError:
            pass  # The cookie is cleared below and the server session expires on its own.
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.session_state["gt_cookie"] = ("", 0)


def go_to(view: str) -> None:
    st.session_state["gt_view"] = view
    st.query_params["view"] = view


def add_to_cart(dish: dict) -> None:
    line = st.session_state["gt_cart"].setdefault(
        dish["dish_id"], {"name": dish["name"], "price": dish["price"], "quantity": 0, "recommended": False})
    line["recommended"] = line["recommended"] or bool(dish.get("from_recommendation"))
    if line["quantity"] >= 10:
        st.toast("Maximum 10 portions per dish", icon=":material/info:")
        return
    line["quantity"] += 1
    st.session_state["gt_cart_open"] = True
    st.toast(f"{dish['name']} added to your cart", icon=":material/shopping_bag:")


def change_quantity(dish_id: str, delta: int) -> None:
    cart = st.session_state["gt_cart"]
    if dish_id not in cart:
        return
    cart[dish_id]["quantity"] = min(cart[dish_id]["quantity"] + delta, 10)
    if cart[dish_id]["quantity"] <= 0:
        cart.pop(dish_id)


def remove_from_cart(dish_id: str) -> None:
    st.session_state["gt_cart"].pop(dish_id, None)


def toggle_cart() -> None:
    st.session_state["gt_cart_open"] = not st.session_state["gt_cart_open"]
