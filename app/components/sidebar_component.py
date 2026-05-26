"""Kiirus sidebar — Streamlit Custom Component wrapper.

The HTML/JS lives in `_html/sidebar/`. This module declares the component
and exposes `render_sidebar()` which renders the iframe and returns the
last event posted from the iframe (or None on first run / no click).
"""
from __future__ import annotations

import os
from typing import Optional, TypedDict

import streamlit.components.v1 as components


_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "_html", "sidebar")

_sidebar = components.declare_component("kiirus_sidebar", path=_PATH)


class SidebarEvent(TypedDict, total=False):
    type: str
    section: str
    theme: str


def render_sidebar(
    active: str,
    theme: str = "dark",
    density: str = "balanced",
    sidebar_width: str = "standard",
    badges: Optional[dict] = None,
    db_meta: str = "",
    version: str = "",
    key: str = "kiirus_sidebar",
) -> Optional[SidebarEvent]:
    """Render the sidebar iframe.

    Args:
        active: the section name that should appear active (e.g. "Landing").
        theme: "dark" or "light".
        density: "compact" / "balanced" / "spacious".
        sidebar_width: "collapsed" / "narrow" / "standard" / "wide".
        badges: optional dict like {"landing": 959, "tat": 856, "transit": 103}.
        db_meta: footer DB line (e.g. "kiirus.db · 12.4 MB").
        version: footer version string (e.g. "v 1.3.0").
        key: Streamlit component key.

    Returns:
        Event dict from the iframe (or None). Shapes:
            {"type": "navigate", "section": "Landing"}
            {"type": "set_theme", "theme": "light"}
            {"type": "toggle_collapse"}
    """
    return _sidebar(
        active=active,
        theme=theme,
        density=density,
        sidebar_width=sidebar_width,
        badges=badges or {},
        db_meta=db_meta,
        version=version,
        key=key,
        default=None,
    )
