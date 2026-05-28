"""Section 3 — Transit (README §14). Non-Delivered shipments triage.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section header with upload trigger.
- Tables use left-border accent (color per Remarks-bucket, RTO grey overrides),
  no full-row tint. Status columns render as pills.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from ..components import chart_pair, data_table, layout
from ..components.theme import render_section_header
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest


NON_DELIVERED_STATUSES = ["Manifested", "Dispatched", "In Transit", "Pending", "RTO"]

DEFAULT_VISIBLE = [
    "Current Status", "Remarks",
    "Days in Transit", "Days Remaining", "Risk Status",
    "Pickup Date", "Destination City", "State", "Pin code",
]

OPTIONAL_VISIBLE = [
    "LRN", "Order id", "Consignee name",
    "Last Scan Date", "Last Scan Location",
    "Additional Remarks", "Promise Date", "Expected Date",
    "Attempt Count", "No of boxes", "Weight", "Payment Type",
    "Package Amount", "First Pending Date", "Master Waybill",
    "_oda", "_origin_zone", "_destination_zone",
]

ALL_TOGGLEABLE = DEFAULT_VISIBLE + OPTIONAL_VISIBLE

DISPLAY_LABEL = {
    "_oda": "ODA",
    "_origin_zone": "Origin Zone",
    "_destination_zone": "Destination Zone",
}


def _bucket_classifier(row: pd.Series) -> Optional[str]:
    """Return one of: 'early' / 'ontime' / 'late' / 'rto' / 'pending' / None.

    Maps Remarks progression buckets onto the left-accent vocabulary.
    RTO overrides Remarks per README §14.6.
    """
    if row.get("Current Status") == "RTO":
        return "rto"
    r = (row.get("Remarks") or "").lower()
    if "out for delivery" in r or "reached destination" in r:
        return "early"   # close to delivery → green accent
    if "in transit" in r or "reached hub" in r:
        return "ontime"  # mid-transit → blue accent
    if "manifested" in r or "dispatched" in r:
        return "ontime"  # early-stage → blue accent
    return "pending"     # exception → amber accent


def _risk_label(days_in_transit, expected_tat_days) -> str:
    """Human-readable risk label for an in-transit shipment."""
    if expected_tat_days is None or days_in_transit is None:
        return ""
    if pd.isna(expected_tat_days) or pd.isna(days_in_transit):
        return ""
    remaining = int(expected_tat_days) - int(days_in_transit)
    if remaining > 0:
        return ""
    elif remaining == 0:
        return "⚠ Due Today"
    else:
        overdue = abs(remaining)
        return f"🔴 At Risk ({overdue}d overdue)"


def _risk_rank(label: str) -> int:
    if label.startswith("🔴"):
        return 2
    if label.startswith("⚠"):
        return 1
    return 0


def _add_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    today = pd.Timestamp(date.today())
    # Transit clock starts at Manifest Date; fall back to Pickup Date when absent.
    manifest = pd.to_datetime(df["Manifest Date"], errors="coerce")
    pickup = pd.to_datetime(df["Pickup Date"], errors="coerce")
    start = manifest.fillna(pickup)
    df["Days in Transit"] = (today - start).dt.days
    exp = pd.to_numeric(df["_expected_tat_days"], errors="coerce")
    days_in_transit_num = pd.to_numeric(df["Days in Transit"], errors="coerce")
    df["Days Remaining"] = (exp - days_in_transit_num).astype("Int64")
    df["Risk Status"] = [
        _risk_label(d, e) for d, e in zip(days_in_transit_num, exp)
    ]
    return df


def render() -> None:
    upload_clicked = render_section_header("Transit", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df = load_latest()
    df = df[df["Current Status"].isin(NON_DELIVERED_STATUSES)]

    if df.empty:
        st.info("No non-Delivered shipments yet.")
        return

    df = _add_derived(df)

    status_filter = st.selectbox(
        "Status filter",
        options=["All"] + NON_DELIVERED_STATUSES,
        key="transit_status_filter",
    )
    if status_filter != "All":
        df = df[df["Current Status"] == status_filter]

    # Default sort: highest risk first, then by Days in Transit desc.
    df = df.copy()
    df["_risk_rank"] = df["Risk Status"].apply(_risk_rank)
    df = df.sort_values(
        ["_risk_rank", "Days in Transit"],
        ascending=[False, False],
        na_position="last",
    )
    df = df.drop(columns=["_risk_rank"])

    left, right = layout.horizontal_split(section_key="transit", default="60/40")

    if left is not None:
        with left:
            _render_table(df)

    if right is not None:
        top, bottom = layout.vertical_split(section_key="transit", container=right)
        chart_pair.render(df, section_key="transit", top_box=top, bottom_box=bottom)


def _render_table(df: pd.DataFrame) -> None:
    visible = data_table.column_picker(
        section_key="transit",
        all_columns=ALL_TOGGLEABLE,
        default_visible=DEFAULT_VISIBLE,
    )
    sort_col, ascending = data_table.sort_controls(
        section_key="transit",
        sortable_columns=visible,
        default_col="Days in Transit",
        default_dir="Desc",
    )
    rename_map = {k: v for k, v in DISPLAY_LABEL.items() if k in df.columns}
    show_df = df.rename(columns=rename_map)
    visible_display = [DISPLAY_LABEL.get(c, c) for c in visible]
    sort_col_display = DISPLAY_LABEL.get(sort_col, sort_col)

    data_table.render_table(
        show_df,
        visible_columns=visible_display,
        sort_col=sort_col_display,
        ascending=ascending,
        row_classifier=_bucket_classifier,
    )
