"""Section 3 — Transit (README §14). Non-Delivered shipments triage.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section header with upload trigger.
- Tables use left-border accent (color per Remarks-bucket, RTO grey overrides),
  no full-row tint. Status columns render as pills.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from typing import Optional

import pandas as pd
import streamlit as st

from ..components import chart_pair, data_table
from ..components.theme import render_section_header
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest


NON_DELIVERED_STATUSES = ["Manifested", "Dispatched", "In Transit", "Pending", "RTO"]

DEFAULT_VISIBLE = [
    "LRN", "Consignee name", "Current Status", "Manifest Date",
    "Expected Date", "Days in Transit", "Days Remaining",
    "Risk Status", "_oda", "Last Scan Date", "Destination City",
    "State", "Pin code",
]

# Same full column universe as before — columns promoted into DEFAULT_VISIBLE
# are removed here to avoid duplicates, and "Remarks" (previously only a
# default) is demoted here so it stays available in the picker.
OPTIONAL_VISIBLE = [
    "Order id", "Remarks", "Last Scan Location",
    "Additional Remarks", "Promise Date",
    "Attempt Count", "No of boxes", "Weight", "Payment Type",
    "Package Amount", "First Pending Date", "Master Waybill",
    "_origin_zone", "_destination_zone",
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
    open_upload_dialog(upload_clicked)

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

    # Full-width transit table — no side charts.
    _render_table(df)

    # Both charts stacked full width below the table.
    top = st.container()
    bottom = st.container()
    chart_pair.render(df, section_key="transit", top_box=top, bottom_box=bottom)


def _render_table(df: pd.DataFrame) -> None:
    visible = data_table.column_picker(
        section_key="transit",
        all_columns=ALL_TOGGLEABLE,
        default_visible=DEFAULT_VISIBLE,
        display_names=DISPLAY_LABEL,
    )
    sort_col, ascending = data_table.sort_controls(
        section_key="transit",
        sortable_columns=visible,
        default_col="Days in Transit",
        default_dir="Desc",
        display_names=DISPLAY_LABEL,
    )
    rename_map = {k: v for k, v in DISPLAY_LABEL.items() if k in df.columns}
    show_df = df.rename(columns=rename_map)
    visible_display = [DISPLAY_LABEL.get(c, c) for c in visible]
    sort_col_display = DISPLAY_LABEL.get(sort_col, sort_col)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        show_df[visible_display].to_excel(writer, index=False)
    buf.seek(0)
    st.download_button(
        label="⬇ Export Excel",
        data=buf.read(),
        file_name=f"kiirus_transit_{datetime.now():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_transit",
    )

    data_table.render_table(
        show_df,
        visible_columns=visible_display,
        sort_col=sort_col_display,
        ascending=ascending,
        row_classifier=_bucket_classifier,
    )
