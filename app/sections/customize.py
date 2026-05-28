"""Section 4 — Customize (README §15). Filter + column-picker → custom table.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section header with upload trigger.
- Filter panel in a bordered card.
- Detail / Aggregate toggle as segmented control.
- Table uses left-border accent + pill status columns + integer formatting.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from ..components import chart_pair, data_table, layout
from ..components.theme import render_section_header, format_int_for_display
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest
from ..store.schema import ZONES


ALL_STATUSES = ["Manifested", "Dispatched", "In Transit", "Pending", "Delivered", "RTO"]

DETAIL_DEFAULT_VISIBLE = [
    "LRN", "Order id", "Current Status",
    "Pickup Date", "Delivered Date",
    "Destination City", "State", "Pin code",
]

DETAIL_ALL_TOGGLEABLE = DETAIL_DEFAULT_VISIBLE + [
    "Consignee name", "Remarks", "Additional Remarks",
    "No of boxes", "Weight", "Payment Type", "Package Amount",
    "Origin City", "Last Scan Date", "Last Scan Location",
    "Expected Date", "Promise Date", "Attempt Count",
    "_oda", "_origin_zone", "_destination_zone",
    "_expected_tat_days", "_actual_tat_days",
    "_tat_variance_days", "_sla_status",
]


def _sla_classifier(row: pd.Series) -> Optional[str]:
    val = row.get("_sla_status")
    if val == "Early":
        return "early"
    if val == "On Time":
        return "ontime"
    if val == "Late":
        return "late"
    return None


def render() -> None:
    upload_clicked = render_section_header("Customize", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df_all = load_latest()
    if df_all.empty:
        st.info("No data yet. Click ↑ Upload above to load a Delhivery file.")
        return

    view_mode = st.segmented_control(
        "View mode",
        options=["Detail", "Aggregate"],
        default="Detail",
        key="customize_view_mode",
    )

    filters = _filter_panel(df_all)

    apply_clicked = st.button("Apply", type="primary", key="customize_apply")
    if apply_clicked:
        st.session_state["_customize_applied"] = True
        st.session_state["_customize_filters"] = filters

    applied = st.session_state.get("_customize_applied", False)
    if not applied:
        st.caption("Set filters above, then click **Apply** to populate the table.")
        return

    df_filtered = _apply_filters(df_all, st.session_state["_customize_filters"])

    if df_filtered.empty:
        st.warning("Filters returned 0 rows.")
        return

    left, right = layout.horizontal_split(section_key="customize", default="60/40")

    if left is not None:
        with left:
            if view_mode == "Aggregate":
                _render_aggregate(df_filtered)
            else:
                _render_detail(df_filtered)

    if right is not None:
        top, bottom = layout.vertical_split(section_key="customize", container=right)
        chart_pair.render(
            df_filtered,
            section_key="customize",
            top_box=top,
            bottom_box=bottom,
            allow_heatmap=True,
        )


def _multiselect_with_all(label: str, options: list[str], key: str, help_txt: str = "") -> list[str]:
    """Multiselect with a 'Select all / Clear' control just above.

    Returns the list of currently-picked values. Empty list = no filter
    (every value matches). The user can also press 'Select all' to make
    'every value' explicit, or 'Clear' to drop the picks.
    """
    state_key = f"_msel_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    c_label, c_all, c_clear = st.columns([6, 1.2, 1])
    c_label.markdown(
        f"<div style='font-size:14px; color:#F5F5F7; margin-bottom:4px;'>"
        f"{label}<span style='color:#5A5A5F'> (empty = all)</span></div>",
        unsafe_allow_html=True,
    )
    if c_all.button("All", key=f"{key}_all", use_container_width=True):
        st.session_state[state_key] = list(options)
        st.rerun()
    if c_clear.button("Clear", key=f"{key}_clear", use_container_width=True):
        st.session_state[state_key] = []
        st.rerun()

    chosen = st.multiselect(
        label,
        options=options,
        default=st.session_state[state_key],
        key=f"ms_{key}",
        label_visibility="collapsed",
        help=help_txt or None,
    )
    st.session_state[state_key] = chosen
    return chosen


def _filter_panel(df: pd.DataFrame) -> dict:
    with st.expander("Filters", expanded=True):
        pickup = pd.to_datetime(df["Pickup Date"], errors="coerce")
        min_d = pickup.min()
        max_d = pickup.max()
        date_range = None
        if pd.notna(min_d) and pd.notna(max_d):
            date_range = st.date_input(
                "Pickup Date range",
                value=(min_d.date(), max_d.date()),
                min_value=min_d.date(),
                max_value=max_d.date(),
                key="customize_pickup_range",
            )

        c1, c2 = st.columns(2)
        with c1:
            origin_zones = _multiselect_with_all("Origin Zone", ZONES, key="cz_oz")
        with c2:
            dest_zones = _multiselect_with_all("Destination Zone", ZONES, key="cz_dz")

        companies = sorted(df["Order id"].dropna().unique().tolist())
        company_pick = _multiselect_with_all("Company", companies, key="cz_company")

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(
                "<div style='font-size:14px; color:#F5F5F7; margin-bottom:4px;'>ODA</div>",
                unsafe_allow_html=True,
            )
            oda_pick = st.selectbox(
                "ODA", options=["Both", "YES", "NO"], key="cz_oda",
                label_visibility="collapsed",
            )
        with c4:
            status_pick = _multiselect_with_all("Current Status", ALL_STATUSES, key="cz_status")

    return {
        "pickup_range": date_range,
        "origin_zones": origin_zones,
        "dest_zones": dest_zones,
        "companies": company_pick,
        "oda": oda_pick,
        "statuses": status_pick,
    }


def _apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    out = df
    if f["pickup_range"] and len(f["pickup_range"]) == 2:
        lo, hi = f["pickup_range"]
        pickup = pd.to_datetime(out["Pickup Date"], errors="coerce")
        out = out[(pickup.dt.date >= lo) & (pickup.dt.date <= hi)]
    if f["origin_zones"]:
        out = out[out["_origin_zone"].isin(f["origin_zones"])]
    if f["dest_zones"]:
        out = out[out["_destination_zone"].isin(f["dest_zones"])]
    if f["companies"]:
        out = out[out["Order id"].isin(f["companies"])]
    if f["oda"] != "Both":
        out = out[out["_oda"] == f["oda"]]
    if f["statuses"]:
        out = out[out["Current Status"].isin(f["statuses"])]
    return out


def _render_detail(df: pd.DataFrame) -> None:
    visible = data_table.column_picker(
        section_key="customize_detail",
        all_columns=DETAIL_ALL_TOGGLEABLE,
        default_visible=DETAIL_DEFAULT_VISIBLE,
    )
    sort_col, ascending = data_table.sort_controls(
        section_key="customize_detail",
        sortable_columns=visible,
        default_col="Pickup Date",
        default_dir="Desc",
    )
    _export_button(df[visible], "customize_detail")
    data_table.render_table(
        df,
        visible_columns=visible,
        sort_col=sort_col,
        ascending=ascending,
        row_classifier=_sla_classifier,
    )


def _render_aggregate(df: pd.DataFrame) -> None:
    """Build the 12-column per-company aggregate (README §15.7)."""
    grouped = df.groupby(df["Order id"].fillna("Unknown"))
    total_overall = len(df)

    agg = pd.DataFrame({
        "Total Orders": grouped.size(),
        "Delivered": grouped.apply(lambda g: int((g["Current Status"] == "Delivered").sum())),
        "In Transit": grouped.apply(lambda g: int((g["Current Status"] == "In Transit").sum())),
        "Pending": grouped.apply(lambda g: int((g["Current Status"] == "Pending").sum())),
        "RTO": grouped.apply(lambda g: int((g["Current Status"] == "RTO").sum())),
        "_early": grouped.apply(lambda g: int((g["_sla_status"] == "Early").sum())),
        "_on_time": grouped.apply(lambda g: int((g["_sla_status"] == "On Time").sum())),
        "_late": grouped.apply(lambda g: int((g["_sla_status"] == "Late").sum())),
        "_oda_yes": grouped.apply(lambda g: int((g["_oda"] == "YES").sum())),
    }).reset_index().rename(columns={"Order id": "Company"})

    agg["Order Share %"] = (100 * agg["Total Orders"] / max(total_overall, 1)).round(1)
    denom_delivered = agg["Delivered"].replace(0, pd.NA)
    agg["On Time %"] = (100 * agg["_on_time"] / denom_delivered).round(1)
    agg["Early %"]   = (100 * agg["_early"]   / denom_delivered).round(1)
    agg["Late %"]    = (100 * agg["_late"]    / denom_delivered).round(1)
    agg["SLA % combined"] = (100 * (agg["_early"] + agg["_on_time"]) / denom_delivered).round(1)
    agg["ODA %"] = (100 * agg["_oda_yes"] / agg["Total Orders"].replace(0, pd.NA)).round(1)

    cols_order = [
        "Company", "Total Orders", "Order Share %",
        "Delivered", "In Transit", "Pending", "RTO",
        "On Time %", "Early %", "Late %",
        "SLA % combined", "ODA %",
    ]
    agg = agg[cols_order].sort_values("Total Orders", ascending=False)
    agg = format_int_for_display(agg)

    _export_button(agg, "customize_aggregate")
    st.dataframe(agg, hide_index=True, use_container_width=True, height=540)


def _export_button(df: pd.DataFrame, key: str) -> None:
    if df.empty:
        return
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    st.download_button(
        "Export Excel",
        data=buf.getvalue(),
        file_name=f"kiirus_{key}_{datetime.now():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"export_{key}",
    )
