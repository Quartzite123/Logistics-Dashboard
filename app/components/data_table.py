"""Shared sortable / column-toggleable table widget.

Streamlit's st.dataframe is a React (glide-data-grid) component, not an HTML
table. The pandas Styler properties it honours are LIMITED: it reliably
renders `color` and `background-color`, but does NOT render `box-shadow`,
`padding`, `border`, or `text-align` reliably. The original spec called for
a 3px coloured left-border accent via box-shadow; that approach broke first-
column rendering (white-banded cells over LRN), so this module now uses a
simpler pattern:

  - SLA status / Stuck / status-like columns render as pills via a tinted
    background-color + bold coloured text on those CELLS only.
  - The 3px left-border accent has been DROPPED. Users see status via the
    pill column and can sort by SLA Status to group rows.

Column-picker order: the user's pick order is preserved (so columns can be
reordered by removing and re-adding them in the desired sequence).
"""
from __future__ import annotations

import sys
from typing import Optional, Callable

import pandas as pd
import streamlit as st

# streamlit-sortables isn't available under stlite/Pyodide, so import it
# optionally and fall back to a plain multiselect column picker when missing.
try:
    from streamlit_sortables import sort_items
    _HAS_SORTABLES = True
except ImportError:
    sort_items = None
    _HAS_SORTABLES = False

from .theme import (
    STATUS_EARLY, STATUS_ONTIME, STATUS_LATE, STATUS_PENDING,
    STATUS_SOFT, STATUS_COLORS,
    format_int_for_display,
)


PILL_COLUMNS = {
    "SLA Status", "_sla_status",
    "Current Status",
    "Risk Status",
    "ODA", "_oda",
}


_SORTABLE_CSS = """
.sortable-component {
  background: transparent;
}
.sortable-container {
  background: #131316;
  border: 1px solid #2A2A2E;
  border-radius: 8px;
  padding: 8px;
  min-height: 64px;
}
.sortable-container-header {
  color: #8E8E93;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  padding: 4px 8px 8px 8px;
}
.sortable-item {
  background: #22222A;
  color: #F5F5F7;
  border: 1px solid #3A3A40;
  border-radius: 6px;
  padding: 6px 12px;
  margin: 4px 4px 4px 0;
  font-size: 13px;
  cursor: grab;
}
.sortable-item:hover {
  border-color: #FFD60A;
}
"""


def _is_stlite() -> bool:
    """True when running under Pyodide/stlite (no Tornado component server)."""
    return sys.platform == "emscripten"


def _picker_controls(
    section_key: str,
    all_columns: list[str],
    default_visible: list[str],
    clear_keys: tuple = (),
) -> None:
    """Caption + Show all / Reset buttons shared by both picker variants.

    clear_keys: extra session_state keys to drop so the underlying widget
    re-initialises (e.g. the sortables component key).
    """
    st.caption(
        "Tap the dropdown to add columns · "
        "Click × on a pill to hide that column"
    )
    state_key = f"_visible_cols_{section_key}"
    ms_key = f"_ms_cols_{section_key}"

    def _apply(cols):
        st.session_state[state_key] = list(cols)
        st.session_state[ms_key] = list(cols)
        for k in clear_keys:
            st.session_state.pop(k, None)

    bc1, bc2 = st.columns(2)
    bc1.button(
        "Show all columns", key=f"showall_{section_key}",
        on_click=lambda: _apply(all_columns), use_container_width=True,
    )
    bc2.button(
        "Reset to defaults", key=f"reset_{section_key}",
        on_click=lambda: _apply(default_visible), use_container_width=True,
    )


def _multiselect_picker(section_key, all_columns, default_visible, label, display_names):
    """stlite fallback: plain multiselect (show/hide; order follows all_columns)."""
    state_key = f"_visible_cols_{section_key}"
    ms_key = f"_ms_cols_{section_key}"
    if ms_key not in st.session_state:
        st.session_state[ms_key] = list(default_visible)
    _fmt = lambda c: (display_names or {}).get(c, c)

    with st.expander(label, expanded=True):
        chosen = st.multiselect(
            "Visible columns",
            options=all_columns,
            format_func=_fmt,
            key=ms_key,
        )
        _picker_controls(section_key, all_columns, default_visible)

    new_visible = [c for c in all_columns if c in chosen] or list(default_visible)
    st.session_state[state_key] = new_visible
    return new_visible


def _sortables_picker(section_key, all_columns, default_visible, label, display_names):
    """Desktop: streamlit-sortables drag-and-drop with friendly labels."""
    state_key = f"_visible_cols_{section_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = list(default_visible)
    visible = st.session_state[state_key]
    hidden = [c for c in all_columns if c not in visible]
    _fmt = lambda c: (display_names or {}).get(c, c)
    _rev = {v: k for k, v in (display_names or {}).items()}
    sortable_key = f"sortable_{section_key}"

    with st.expander(label, expanded=False):
        result = sort_items(
            items=[
                {"header": "Visible (left → right = display order)",
                 "items": [_fmt(c) for c in visible]},
                {"header": "Hidden", "items": [_fmt(c) for c in hidden]},
            ],
            multi_containers=True,
            direction="horizontal",
            custom_style=_SORTABLE_CSS,
            key=sortable_key,
        )
        _picker_controls(section_key, all_columns, default_visible,
                         clear_keys=(sortable_key,))

    # Convert the friendly labels back to internal column names.
    if result and len(result) > 0:
        new_visible = [_rev.get(lbl, lbl) for lbl in result[0]["items"]]
    else:
        new_visible = visible
    st.session_state[state_key] = new_visible
    return new_visible


def column_picker(
    section_key: str,
    all_columns: list[str],
    default_visible: list[str],
    label: str = "Columns — drag to reorder, drag between containers to show/hide",
    display_names: Optional[dict] = None,
) -> list[str]:
    """Column show/hide + reorder picker. Returns visible columns (internal names).

    Desktop uses the streamlit-sortables drag-and-drop picker (Tornado serves
    its frontend); stlite/Pyodide — where that component can't load — falls back
    to a plain multiselect. `_HAS_SORTABLES` guards the rare case of the package
    being absent on desktop. Both paths show friendly labels via display_names.
    """
    if _is_stlite() or not _HAS_SORTABLES:
        return _multiselect_picker(section_key, all_columns, default_visible, label, display_names)
    return _sortables_picker(section_key, all_columns, default_visible, label, display_names)


def sort_controls(
    section_key: str,
    sortable_columns: list[str],
    default_col: str,
    default_dir: str = "Desc",
    display_names: Optional[dict] = None,
) -> tuple[str, bool]:
    """Render Sort By + Direction. Returns (col, ascending_bool).

    `display_names` maps internal column names to friendly labels for display.
    """
    if not sortable_columns:
        return "", True
    _fmt = lambda c: (display_names or {}).get(c, c)
    c1, c2 = st.columns([3, 1])
    default_idx = sortable_columns.index(default_col) if default_col in sortable_columns else 0
    col = c1.selectbox(
        "Sort By",
        options=sortable_columns,
        index=default_idx,
        format_func=_fmt,
        key=f"sort_col_{section_key}",
    )
    direction = c2.selectbox(
        "Direction",
        options=["Asc", "Desc"],
        index=0 if default_dir == "Asc" else 1,
        key=f"sort_dir_{section_key}",
    )
    return col, (direction == "Asc")


def _pill_styler(view: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Build a Styler that colours status-like cells as pills (bg tint + bold text).

    Only properties that st.dataframe reliably renders are used:
    background-color, color, font-weight.
    """
    styler = view.style

    status_cols = [c for c in view.columns if c in PILL_COLUMNS]

    if status_cols:
        def _pill(val):
            if pd.isna(val) or val == "":
                return ""
            sval = str(val).strip()
            if sval.startswith("🔴"):
                bg, col = STATUS_SOFT.get("Late"), STATUS_LATE
            elif sval.startswith("⚠"):
                bg, col = STATUS_SOFT.get("Pending"), STATUS_PENDING
            elif sval == "YES":
                bg, col = STATUS_SOFT.get("Late"), STATUS_LATE
            elif sval == "NO":
                bg, col = STATUS_SOFT.get("On Time"), STATUS_ONTIME
            else:
                bg = STATUS_SOFT.get(sval)
                col = STATUS_COLORS.get(sval)
            if not bg or not col:
                return ""
            return f"background-color: {bg}; color: {col}; font-weight: 600;"

        styler = styler.map(_pill, subset=status_cols)

    return styler


def render_table(
    df: pd.DataFrame,
    visible_columns: list[str],
    sort_col: str,
    ascending: bool,
    row_classifier: Optional[Callable[[pd.Series], Optional[str]]] = None,
    height: int = 540,
) -> None:
    """Render the table. `row_classifier` is accepted for API compatibility but
    ignored — the left-border accent was dropped because Streamlit's dataframe
    cannot render box-shadow reliably (see module docstring)."""
    if df.empty:
        st.info("No rows to display.")
        return

    if sort_col and sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=ascending, na_position="last")

    cols_to_show = [c for c in visible_columns if c in df.columns]
    if not cols_to_show:
        st.warning("No columns selected — pick at least one column to display.")
        return

    view = df[cols_to_show]
    view = format_int_for_display(view)

    styler = _pill_styler(view)
    st.dataframe(styler, hide_index=True, use_container_width=True, height=height)
