"""Section 2 — TAT Analysis (README §13). Delivered-only spreadsheet.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section header with upload trigger.
- Table uses left-border SLA accent (no full-row tint), pill status column,
  integer-typed numeric columns.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from ..components import chart_pair, data_table, layout
from ..components.theme import render_section_header
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest


DEFAULT_VISIBLE = [
    "LRN", "Order id", "Current Status",
    "Manifest Date", "Delivered Date",
    "_oda", "_expected_tat_days", "_actual_tat_days",
    "_tat_variance_days", "_sla_status",
]

OPTIONAL_VISIBLE = [
    "Consignee name", "Additional Remarks", "No of boxes", "Weight",
    "Payment Type", "Package Amount", "Pin code",
    "_origin_zone", "_destination_zone",
]

ALL_TOGGLEABLE = DEFAULT_VISIBLE + OPTIONAL_VISIBLE

DISPLAY_LABEL = {
    "_oda": "ODA",
    "_expected_tat_days": "Expected TAT",
    "_actual_tat_days": "Actual TAT",
    "_tat_variance_days": "TAT Variance",
    "_sla_status": "SLA Status",
    "_origin_zone": "Origin Zone",
    "_destination_zone": "Destination Zone",
}


def _sla_classifier(row: pd.Series) -> Optional[str]:
    """Return one of: 'early' / 'ontime' / 'late' / None — used for left accent."""
    val = row.get("SLA Status") or row.get("_sla_status")
    if val == "Early":
        return "early"
    if val == "On Time":
        return "ontime"
    if val == "Late":
        return "late"
    return None


def render() -> None:
    upload_clicked = render_section_header("TAT Analysis", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df = load_latest()
    df = df[df["Current Status"] == "Delivered"]
    df = df[df["Manifest Date"].notna() & df["Delivered Date"].notna()]

    if df.empty:
        st.info("No Delivered shipments yet. Click ↑ Upload above to load a Delhivery file.")
        return

    # SLA filter dropdown
    sla_filter = st.selectbox(
        "SLA filter",
        options=["All", "Early", "On Time", "Late"],
        key="tat_sla_filter",
    )
    if sla_filter != "All":
        df = df[df["_sla_status"] == sla_filter]

    left, right = layout.horizontal_split(section_key="tat", default="60/40")

    if left is not None:
        with left:
            _render_table(df)

    if right is not None:
        top, bottom = layout.vertical_split(section_key="tat", container=right)
        chart_pair.render(df, section_key="tat", top_box=top, bottom_box=bottom)


def _render_table(df: pd.DataFrame) -> None:
    visible = data_table.column_picker(
        section_key="tat",
        all_columns=ALL_TOGGLEABLE,
        default_visible=DEFAULT_VISIBLE,
    )
    sort_col, ascending = data_table.sort_controls(
        section_key="tat",
        sortable_columns=visible,
        default_col="Manifest Date",
        default_dir="Desc",
    )

    rename_map = {k: v for k, v in DISPLAY_LABEL.items() if k in df.columns and k in visible}
    show_df = df.rename(columns=rename_map)
    visible_display = [DISPLAY_LABEL.get(c, c) for c in visible]
    sort_col_display = DISPLAY_LABEL.get(sort_col, sort_col)

    data_table.render_table(
        show_df,
        visible_columns=visible_display,
        sort_col=sort_col_display,
        ascending=ascending,
        row_classifier=_sla_classifier,
    )
