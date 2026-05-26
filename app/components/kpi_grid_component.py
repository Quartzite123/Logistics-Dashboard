"""Kiirus KPI grid — Streamlit Custom Component wrapper.

Renders the 12-card KPI grid as a single iframe with the full design system
inlined. Replaces the inline-style cards previously rendered by
`kpi_cards.py` so the markup is bulletproof against Streamlit re-wraps.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import streamlit.components.v1 as components


_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "_html", "kpi_grid")

_kpi_grid = components.declare_component("kiirus_kpi_grid", path=_PATH)


def render_kpi_grid(
    rows: list[dict[str, Any]],
    theme: str = "dark",
    density: str = "balanced",
    key: str = "kiirus_kpi_grid",
) -> Optional[Any]:
    """Render the KPI grid.

    Args:
        rows: list of row dicts. Each row has:
            {
                "cols": 3 | 4 | 2,
                "cards": [
                    {
                        "label": "Total Orders",
                        "value": "959",        # str or number
                        "value_color": "primary"  # primary|ok|warn|bad|info|accent
                        "accent": True,           # adds kpi-accent class
                        "date_range": False,
                        "date_from": "25 Nov 2025",   # only if date_range
                        "date_to":   "24 Feb 2026",
                        "unit": "pincodes",            # optional suffix
                        "meta": "all shipments",
                        "delta": "+12.4%",
                        "delta_kind": "up" | "down" | "flat",
                        "progress": {"value": 89.3, "kind": "ok"},  # optional
                        "spark": [..numbers..],                       # optional
                        "icon": "<svg>...</svg>",                     # optional inline svg/text
                    },
                    ...
                ],
            }
        theme: "dark" or "light".
        density: "compact" / "balanced" / "spacious".
        key: Streamlit component key.
    """
    return _kpi_grid(
        rows=rows,
        theme=theme,
        density=density,
        key=key,
        default=None,
    )
