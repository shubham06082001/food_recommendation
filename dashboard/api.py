"""Thin HTTP client: the dashboard reads and writes ECOS data only through the FastAPI backend."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_URL = os.getenv("ECOS_API_URL", "http://localhost:8000/api/v1").rstrip("/")


class ApiError(Exception):
    """A backend call failed; the message is safe to show to the user."""


@st.cache_resource
def _client() -> httpx.Client:
    # trust_env=False keeps corporate proxy settings from intercepting localhost calls.
    return httpx.Client(base_url=API_URL, timeout=30.0, trust_env=False)


def _message(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        return response.text or response.reason_phrase
    if isinstance(detail, list):
        return "; ".join(f"{'.'.join(map(str, d.get('loc', [])[1:]))}: {d.get('msg')}" for d in detail)
    return str(detail)


def request(method: str, path: str, **kwargs: Any) -> Any:
    headers = kwargs.pop("headers", {})
    if user_id := st.session_state.get("user_id"):
        headers["X-User-Id"] = user_id
    try:
        response = _client().request(method, path, headers=headers, **kwargs)
    except httpx.HTTPError as error:
        raise ApiError(f"Cannot reach the ECOS backend at {API_URL}. Is it running?") from error
    if response.status_code >= 400:
        raise ApiError(_message(response))
    return response.json()


def is_backend_up() -> bool:
    try:
        return _client().get("/health", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


def get(path: str, **params: Any) -> Any:
    return request("GET", path, params={k: v for k, v in params.items() if v is not None})


def post(path: str, json: dict | None = None, **kwargs: Any) -> Any:
    return request("POST", path, json=json, **kwargs)


def put(path: str, json: dict) -> Any:
    return request("PUT", path, json=json)


def patch(path: str, json: dict) -> Any:
    return request("PATCH", path, json=json)


@st.cache_data(ttl=10, show_spinner=False)
def recommendations(user_id: str, meal_period: str | None, query: str, limit: int, exclude: tuple) -> dict:
    """Live engine call; the short TTL only absorbs Streamlit reruns. user_id keys the cache per user."""
    return post("/recommendations", {"meal_period": meal_period, "query": query, "limit": limit,
                                    "exclude_dish_ids": list(exclude)})


@st.cache_data(ttl=10, show_spinner=False)
def meal_plan(user_id: str, query: str) -> dict:
    """Live day plan; user_id keys the short-lived cache per user."""
    return post("/recommendations/meal-plan", {"query": query})


def load(path: str, **params: Any) -> Any | None:
    """GET for page rendering: shows the error inline and returns None instead of raising."""
    try:
        return get(path, **params)
    except ApiError as error:
        st.error(str(error), icon=":material/cloud_off:")
        return None
