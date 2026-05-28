"""Kiirus Xpress dashboard — Streamlit entry point.

Run locally:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import streamlit as st

from app.store.db import init_db
from app.store.seed import seed_all_if_empty
from app.sections import landing, aggregate, tat, transit, customize, edit
from app.components.global_styles import inject_global_styles
from app.components.theme import ensure_session_defaults
from app.components import sidebar_component


# ---- one-time setup -------------------------------------------------------
st.set_page_config(
    page_title="Kiirus Xpress — Logistics Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
seed_all_if_empty()


# ---- nav definition -------------------------------------------------------
NAV_ITEMS: list[tuple[str, callable]] = [
    ("Landing",      landing.render),
    ("Aggregate",    aggregate.render),
    ("TAT Analysis", tat.render),
    ("Transit",      transit.render),
    ("Customize",    customize.render),
    ("Edit",         edit.render),
]
SECTIONS: dict[str, callable] = dict(NAV_ITEMS)


def _handle_sidebar_event(event: dict | None) -> None:
    """Apply a sidebar event to session_state and rerun if anything changed."""
    if not event or not isinstance(event, dict):
        return
    ev_type = event.get("type")

    if ev_type == "navigate":
        section = event.get("section")
        if section and section in SECTIONS and section != st.session_state["current_section"]:
            st.session_state["current_section"] = section
            st.rerun()

    elif ev_type == "set_theme":
        new_theme = event.get("theme")
        if new_theme in ("dark", "light") and new_theme != st.session_state["theme_mode"]:
            st.session_state["theme_mode"] = new_theme
            st.rerun()

    elif ev_type == "toggle_theme":
        st.session_state["theme_mode"] = (
            "light" if st.session_state["theme_mode"] == "dark" else "dark"
        )
        st.rerun()

    elif ev_type == "toggle_collapse":
        current = st.session_state["sidebar_width"]
        st.session_state["sidebar_width"] = "collapsed" if current != "collapsed" else "standard"
        st.rerun()


def _render_sidebar() -> str:
    """Render the iframe-based sidebar and return the active section name."""
    with st.sidebar:
        event = sidebar_component.render_sidebar(
            active=st.session_state["current_section"],
            theme=st.session_state["theme_mode"],
            density=st.session_state["density"],
            sidebar_width=st.session_state["sidebar_width"],
            db_meta="kiirus.db",
            version="v 1.0.0",
        )
    _handle_sidebar_event(event)
    return st.session_state["current_section"]


def main() -> None:
    # Session state defaults — must come first
    if "current_section" not in st.session_state:
        st.session_state["current_section"] = "Landing"
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "dark"
    if "sidebar_width" not in st.session_state:
        st.session_state["sidebar_width"] = "standard"
    if "density" not in st.session_state:
        st.session_state["density"] = "balanced"

    inject_global_styles()

    current = _render_sidebar()
    render_fn = SECTIONS.get(current) or SECTIONS["Landing"]
    render_fn()


if __name__ == "__main__":
    main()
