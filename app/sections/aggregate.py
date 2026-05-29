"""Section — Aggregate (per-company breakdown).

A founder-facing summary reachable directly from the sidebar (no need to
go through Customize). Shows:
 1. A per-company summary table (+ Excel export).
 2. A grouped bar chart — Early / On Time / Late % by company.
 3. A per-company monthly stacked bar (company picker; full list, top
    volume first).
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..components.theme import (
    render_section_header,
    get_plotly_layout,
    STATUS_EARLY, STATUS_ONTIME, STATUS_LATE, STATUS_RTO,
)
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import get_aggregate_by_company, get_monthly_by_company


def render() -> None:
    upload_clicked = render_section_header("Aggregate", show_upload_button=True)
    open_upload_dialog(upload_clicked)

    agg = get_aggregate_by_company()
    if agg.empty:
        st.info("No shipments yet. Click ↑ Upload above to load a Delhivery file.")
        return

    # Percentages computed from the delivered count (NA-safe on 0 delivered).
    delivered = agg["delivered"].replace(0, pd.NA)
    agg["early_pct"]   = (agg["early"]   / delivered * 100).round(1)
    agg["on_time_pct"] = (agg["on_time"] / delivered * 100).round(1)
    agg["late_pct"]    = (agg["late"]    / delivered * 100).round(1)
    agg["sla_pct"]     = ((agg["early"] + agg["on_time"]) / delivered * 100).round(1)

    _render_table(agg)
    _render_grouped_bar(agg)
    _render_monthly_stacked()


def _render_table(agg: pd.DataFrame) -> None:
    display = agg.rename(columns={
        "company": "Company",
        "total_orders": "Total Orders",
        "order_share_pct": "Order Share %",
        "delivered": "Delivered",
        "in_transit": "In Transit",
        "rto": "RTO",
        "early_pct": "Early %",
        "on_time_pct": "On Time %",
        "late_pct": "Late %",
        "sla_pct": "SLA %",
    })[[
        "Company", "Total Orders", "Order Share %", "Delivered", "In Transit",
        "RTO", "Early %", "On Time %", "Late %", "SLA %",
    ]]

    st.dataframe(display, hide_index=True, use_container_width=True, height=440)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        display.to_excel(writer, index=False)
    buf.seek(0)
    st.download_button(
        label="⬇ Export Excel",
        data=buf.read(),
        file_name=f"kiirus_aggregate_{datetime.now():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_aggregate",
    )


def _render_grouped_bar(agg: pd.DataFrame) -> None:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg["company"], y=agg["early_pct"], name="Early %",
        marker_color=STATUS_EARLY,
    ))
    fig.add_trace(go.Bar(
        x=agg["company"], y=agg["on_time_pct"], name="On Time %",
        marker_color=STATUS_ONTIME,
    ))
    fig.add_trace(go.Bar(
        x=agg["company"], y=agg["late_pct"], name="Late %",
        marker_color=STATUS_LATE,
    ))
    fig.update_layout(
        title="Delivery Performance by Company",
        barmode="group",
        yaxis_title="Percent of delivered",
        xaxis_title=None,
        **get_plotly_layout(),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_monthly_stacked() -> None:
    mbc = get_monthly_by_company()
    if mbc.empty:
        return

    # Companies ordered by total volume — top 5 surface first in the picker.
    totals = mbc.groupby("company")["total"].sum().sort_values(ascending=False)
    companies = totals.index.tolist()

    choice = st.selectbox(
        "Company — monthly breakdown",
        options=companies,
        key="aggregate_company_pick",
    )

    sub = mbc[mbc["company"] == choice].sort_values("month").copy()
    if sub.empty:
        st.info("No monthly data for this company.")
        return

    sub["month_label"] = pd.to_datetime(sub["month"] + "-01").dt.strftime("%b %Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=sub["month_label"], y=sub["early"],         name="Early",         marker_color=STATUS_EARLY))
    fig.add_trace(go.Bar(x=sub["month_label"], y=sub["on_time"],       name="On Time",       marker_color=STATUS_ONTIME))
    fig.add_trace(go.Bar(x=sub["month_label"], y=sub["late"],          name="Late",          marker_color=STATUS_LATE))
    fig.add_trace(go.Bar(x=sub["month_label"], y=sub["not_delivered"], name="Not Delivered", marker_color=STATUS_RTO))
    fig.update_layout(
        title=f"Monthly Breakdown — {choice}",
        barmode="stack",
        yaxis_title="Number of Orders",
        xaxis_title=None,
        **get_plotly_layout(),
    )
    st.plotly_chart(fig, use_container_width=True)
