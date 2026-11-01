"""Visual theme: the ECOS color system, type scale, and responsive rules."""

from __future__ import annotations

import streamlit as st


def apply_canva_theme() -> None:
    """Inject the exact ECOS color system, type scale, and responsive rules."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');
        :root {
          --bg-page: #f6f3eb; --ink: #19352d; --muted: #718078;
          --sidebar-bg: #153d31; --sidebar-text: #edf6ec; --sidebar-dim: #d5e4da; --sidebar-dimmer: #b9d0c3;
          --sidebar-active: #2a5b49; --pill-active-bg: #eef7e7; --pill-active-text: #164535;
          --card-bg: #ffffff; --card-border: #e4e7df; --btn-primary: #174a3a; --btn-secondary-bg: #e9f1e7;
          --badge-live-bg: #dcfce7; --badge-live-text: #166534; --badge-critical-bg: #f8e4e0; --badge-critical-text: #a34539;
          --badge-amber-bg: #fef3c7; --badge-amber-text: #92400e; --badge-healthy-text: #15803d;
        }
        [data-testid="stAppViewContainer"] { background: var(--bg-page); color: var(--ink); font-family: 'DM Sans', sans-serif; }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stMainBlockContainer"] { max-width: 1360px; padding-top: 1.4rem; }
        /* Set color once on the container and let it inherit, rather than forcing every descendant;
           forcing "*" directly targets nested <p> tags (buttons, metrics) and wins over child overrides. */
        [data-testid="stSidebar"] { background: var(--sidebar-bg); color: var(--sidebar-text); font-family: 'DM Sans', sans-serif; }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--sidebar-dimmer) !important; }
        h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; color: var(--ink) !important; font-weight: 700 !important; letter-spacing: 0 !important; }
        .gt-kicker { color: #277653; font-weight: 700; font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; }
        .gt-muted { color: var(--muted); font-size: 0.92rem; }
        [data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
          background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 18px;
          box-shadow: 0 8px 24px rgba(21, 61, 49, 0.05);
        }
        [data-testid="stMetric"] { padding: 1.05rem 1.1rem; }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; }
        [data-testid="stMetricValue"] { font-family: 'Fraunces', serif !important; color: var(--ink) !important; }
        [data-testid="stButton"] button {
          border-radius: 10px; border: 1px solid var(--card-border); font-weight: 700; font-size: 0.85rem;
          background: var(--btn-secondary-bg); color: var(--btn-primary); transition: transform 150ms ease, box-shadow 150ms ease;
        }
        [data-testid="stButton"] button:hover { transform: translateY(-1px); box-shadow: 0 6px 14px rgba(23, 74, 58, 0.14); }
        [data-testid="stButton"] button[kind="primary"] { background: var(--btn-primary); border-color: var(--btn-primary); color: #fff; }
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--sidebar-text) !important; }
        [data-testid="stSidebar"] hr { border-color: var(--sidebar-active); }
        [data-testid="stSidebar"] [data-testid="stButton"] button {
          background: transparent; border: 1px solid var(--sidebar-active); border-radius: 9px; box-shadow: none;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button :is(p, span) { color: var(--sidebar-dim) !important; font-weight: 700; }
        [data-testid="stSidebar"] [class*="st-key-nav_"] button { border-color: transparent; justify-content: flex-start; padding-left: 0.9rem; }
        [data-testid="stSidebar"] [class*="st-key-nav_"] button > div { justify-content: flex-start; width: 100%; }
        [data-testid="stSidebar"] [class*="st-key-nav_"] button :is(p, span) { color: var(--sidebar-dimmer) !important; }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover { background: var(--sidebar-active); transform: none; box-shadow: none; }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover :is(p, span) { color: #fff !important; }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] { background: var(--pill-active-bg); border-color: var(--pill-active-bg); }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] :is(p, span) { color: var(--pill-active-text) !important; }
        .gt-avatar { display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem; border-radius: 9999px;
          background: var(--pill-active-bg); color: var(--pill-active-text); font-weight: 700; margin-right: 0.55rem; }
        .gt-user { display: flex; align-items: center; color: var(--sidebar-text); line-height: 1.25; }
        .gt-user small { color: var(--sidebar-dimmer); }
        [data-testid="stDataFrame"] { border: 1px solid var(--card-border); border-radius: 14px; overflow: hidden; }
        .gt-pill { display: inline-block; padding: 0.22rem 0.65rem; border-radius: 9999px; font-weight: 700; font-size: 0.72rem; }
        .pill-live { background: var(--badge-live-bg); color: var(--badge-live-text); }
        .pill-healthy { background: #e8f8ee; color: var(--badge-healthy-text); }
        .pill-amber { background: var(--badge-amber-bg); color: var(--badge-amber-text); }
        .pill-critical { background: var(--badge-critical-bg); color: var(--badge-critical-text); }
        .gt-hero { background: #eef6e8; border: 1px solid #dcebd7; border-radius: 18px; padding: 1.2rem 1.35rem; }
        .gt-dish-card { font-family: 'DM Sans', sans-serif; }
        /* Cart: light card inside the dark sidebar; selectors outrank the sidebar's own button/text rules. */
        [data-testid="stSidebar"] .st-key-gt_cart_panel { background: var(--card-bg); border: 1px solid var(--card-border);
          border-radius: 16px; padding: 0.9rem 0.9rem 0.7rem; margin: 0.2rem 0 0.6rem; color: var(--ink);
          box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18); }
        [data-testid="stSidebar"] .st-key-gt_cart_panel :is(h4, p, span, b, div) { color: var(--ink) !important; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel .gt-kicker { color: #277653 !important; margin: 0; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel .gt-cart-title { font-family: 'Fraunces', serif; margin: 0; padding: 0; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stButton"] button {
          background: var(--btn-secondary-bg); border: 1px solid var(--card-border); min-height: 2.1rem;
          padding: 0 0.4rem; justify-content: center; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stButton"] button :is(p, span) { color: var(--btn-primary) !important; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stButton"] button:hover { background: #dbe9d8; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stButton"] button[kind="primary"] { background: var(--btn-primary); border-color: var(--btn-primary); }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [data-testid="stButton"] button[kind="primary"] :is(p, span) { color: #fff !important; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel .st-key-gt_cart_close button { background: transparent; border: none; }
        [data-testid="stSidebar"] .st-key-gt_cart_panel [class*="st-key-remove_"] button :is(p, span) { color: var(--badge-critical-text) !important; }
        .gt-qty { text-align: center; font-weight: 700; }
        .gt-cart-line { display: flex; justify-content: space-between; gap: 0.5rem; font-weight: 600; margin-top: 0.4rem; }
        .gt-cart-total { display: flex; justify-content: space-between; align-items: baseline; margin: 0.6rem 0 0.7rem;
          padding-top: 0.6rem; border-top: 1px dashed var(--card-border); }
        .gt-cart-total b { font-family: 'Fraunces', serif; font-size: 1.3rem; }
        [data-testid="stSidebar"] .st-key-sign_out button { border-color: transparent; justify-content: flex-start; padding-left: 0.9rem; }
        [data-testid="stSidebar"] .st-key-sign_out button > div { justify-content: flex-start; width: 100%; }
        /* Dish cards */
        .gt-card-img { width: 100%; height: 170px; object-fit: cover; border-radius: 14px; display: block; background: #eef3ea; }
        .gt-card-noimg { height: 170px; border-radius: 14px; background: #eef6e8; display: flex; align-items: center;
          justify-content: center; font-size: 3rem; }
        .gt-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-top: 0.7rem; }
        .gt-card-name { font-family: 'Fraunces', serif; font-weight: 700; font-size: 1.08rem; color: var(--ink); line-height: 1.25; }
        .gt-score { background: var(--pill-active-bg); color: var(--pill-active-text); border-radius: 9999px; padding: 0.15rem 0.55rem;
          font-weight: 700; font-size: 0.72rem; white-space: nowrap; }
        .gt-card-sub { color: var(--muted); font-size: 0.86rem; margin: 0.15rem 0 0.55rem; }
        .gt-macros { display: grid; grid-template-columns: repeat(auto-fit, minmax(52px, 1fr)); gap: 0.35rem; margin-bottom: 0.5rem; }
        .gt-macros div { background: #f4f7f1; border-radius: 10px; padding: 0.35rem 0.2rem; text-align: center; line-height: 1.1; }
        .gt-macros b { display: block; color: var(--ink); font-size: 0.92rem; }
        .gt-macros small { color: var(--muted); font-size: 0.68rem; }
        .gt-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.3rem; }
        .gt-chip { border: 1px solid var(--card-border); border-radius: 9999px; padding: 0.1rem 0.5rem; font-size: 0.72rem; color: #4b5d55; }
        .gt-chip.warn { background: #fff4e5; border-color: #f5d7a8; color: #92400e; }
        .gt-credit { font-size: 0.62rem; color: var(--muted); text-align: right; margin-top: 0.15rem; }
        .gt-credit a { color: var(--muted); }
        @media (max-width: 700px) {
          [data-testid="stMainBlockContainer"] { padding-top: 1rem; }
          h1 { font-size: 1.7rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
