"""Section — Aggregate Transit (per-company undelivered-orders breakdown).

Company picker -> two side-by-side summary tables (risk-status counts + days-
overdue distribution) -> full orders table -> 2-sheet Excel export.

Risk Status logic mirrors transit.py:
  days_remaining = _expected_tat_days - days_in_transit
  - days_remaining < 0  -> "At Risk"
  - days_remaining == 0 -> "Due Today"
  - days_remaining > 0  -> "On Track"
  - _expected_tat_days NULL (or days_remaining NaN) -> "Pending"
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st

from ..components.theme import render_section_header
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import (
    get_undelivered_by_company,
    get_undelivered_orders,
    get_all_undelivered,
)


RISK_COLORS = {
    "At Risk":   "#F87171",
    "Due Today": "#FBBF24",
    "On Track":  "#4ADE80",
    "Pending":   "#94A3B8",
}
RISK_ORDER = ["At Risk", "Due Today", "On Track", "Pending"]


def _add_risk_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Add Risk Status / days_in_transit / days_remaining / days_overdue."""
    today = pd.Timestamp(date.today())
    df = df.copy()
    df["manifest_date_parsed"] = pd.to_datetime(df["manifest_date"], errors="coerce")
    df["days_in_transit"] = (today - df["manifest_date_parsed"]).dt.days
    df["days_remaining"] = df["_expected_tat_days"] - df["days_in_transit"]

    def risk_label(row):
        if pd.isna(row["_expected_tat_days"]):
            return "Pending"
        r = row["days_remaining"]
        if pd.isna(r):
            return "Pending"
        if r < 0:
            return "At Risk"
        if r == 0:
            return "Due Today"
        return "On Track"

    df["Risk Status"] = df.apply(risk_label, axis=1)
    df["days_overdue"] = (
        df["days_in_transit"] - df["_expected_tat_days"]
    ).clip(lower=0)
    return df


def _style_risk(val: object) -> str:
    color = RISK_COLORS.get(val if isinstance(val, str) else "", "")
    if not color:
        return ""
    return f"background-color: {color}; color: #0A0A0B; font-weight: 600;"


def render() -> None:
    upload_clicked = render_section_header("Aggregate Transit", show_upload_button=True)
    open_upload_dialog(upload_clicked)

    # ---- Company dropdown ------------------------------------------------
    companies_df = get_undelivered_by_company()
    if companies_df.empty:
        st.info("No undelivered shipments. Upload a Delhivery file to populate this view.")
        return

    selected = st.selectbox(
        "Company (sorted by undelivered count, descending)",
        options=companies_df["company"].tolist(),
        key="agg_transit_company",
    )

    orders = _add_risk_cols(get_undelivered_orders(selected))

    # ---- Two side-by-side tables ----------------------------------------
    col_l, col_r = st.columns([1, 1])

    with col_l:
        st.markdown("**Risk Status Summary**")
        counts = orders["Risk Status"].value_counts()
        total = int(len(orders))
        summary_rows = []
        for rs in RISK_ORDER:
            n = int(counts.get(rs, 0))
            pct = (100.0 * n / total) if total else 0.0
            summary_rows.append({
                "Risk Status": rs,
                "Orders": n,
                "% of Total": f"{pct:.1f}%",
            })
        summary_df = pd.DataFrame(summary_rows)
        styled = summary_df.style.applymap(_style_risk, subset=["Risk Status"])
        st.dataframe(styled, hide_index=True, use_container_width=True)

    with col_r:
        st.markdown("**Days Overdue breakdown**")
        overdue = orders[orders["days_overdue"] > 0]
        if overdue.empty:
            placeholder = pd.DataFrame(
                [{"Days Overdue": "No overdue orders", "Orders": ""}]
            )

            def _green(val):
                if val == "No overdue orders":
                    return "background-color: #4ADE80; color: #0A0A0B; font-weight: 600;"
                return ""

            styled = placeholder.style.applymap(_green, subset=["Days Overdue"])
            st.dataframe(styled, hide_index=True, use_container_width=True)
        else:
            grouped = (
                overdue.assign(_d=overdue["days_overdue"].astype(int))
                .groupby("_d")
                .size()
                .reset_index(name="Orders")
                .rename(columns={"_d": "Days Overdue"})
                .sort_values("Days Overdue")
                .reset_index(drop=True)
            )
            st.dataframe(grouped, hide_index=True, use_container_width=True)

    # ---- Full individual orders table -----------------------------------
    st.markdown("---")
    st.markdown(f"**Individual orders — {selected}**")
    display_orders = orders.copy()
    display_orders["Days in Transit"] = display_orders["days_in_transit"]
    display_orders["Days Remaining"] = display_orders["days_remaining"]
    display_orders = display_orders.sort_values(
        "days_in_transit", ascending=False, na_position="last"
    )
    drop_cols = ["manifest_date_parsed", "days_in_transit", "days_remaining", "days_overdue"]
    display_orders = display_orders.drop(
        columns=[c for c in drop_cols if c in display_orders.columns]
    )

    styled_orders = display_orders.style.applymap(_style_risk, subset=["Risk Status"])
    st.dataframe(styled_orders, hide_index=True, use_container_width=True)

    # ---- Excel download (2 sheets) --------------------------------------
    all_undelivered = _add_risk_cols(get_all_undelivered())
    if all_undelivered.empty:
        summary_per_co = pd.DataFrame(
            columns=["Company", "Total Undelivered"] + RISK_ORDER + ["% At Risk"]
        )
    else:
        pivot = (
            all_undelivered.groupby("order_id")["Risk Status"]
            .value_counts()
            .unstack(fill_value=0)
            .reindex(columns=RISK_ORDER, fill_value=0)
            .reset_index()
        )
        pivot.columns.name = None
        pivot = pivot.rename(columns={"order_id": "Company"})
        pivot["Total Undelivered"] = pivot[RISK_ORDER].sum(axis=1)
        denom = pivot["Total Undelivered"].replace(0, pd.NA)
        pivot["% At Risk"] = (100 * pivot["At Risk"] / denom).round(1).fillna(0)
        summary_per_co = pivot[
            ["Company", "Total Undelivered"] + RISK_ORDER + ["% At Risk"]
        ].sort_values("Total Undelivered", ascending=False)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary_per_co.to_excel(writer, sheet_name="Summary", index=False)
        display_orders.to_excel(writer, sheet_name="Orders", index=False)
    buf.seek(0)
    st.download_button(
        label="⬇ Export Excel",
        data=buf.read(),
        file_name=f"kiirus_transit_{selected}_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_aggregate_transit",
    )
