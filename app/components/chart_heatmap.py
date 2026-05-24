"""Customize-only Heatmap with full polish (README §17.5).

Restyled per CLAUDE_CODE_UI_PROMPT.md: dark Plotly palette + black→yellow gradient.
- Volume-aware cell text: '% (n=count)'
- Rows sorted by total volume desc
- Toggles: granularity (State / Zone), metric (Late % / SLA % / Avg TAT)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from .theme import (
    apply_plotly_defaults,
    HEATMAP_COLORSCALE,
    YELLOW_PRIMARY,
    BG_BASE,
    STATUS_EARLY, STATUS_LATE,
)
from .chart_expand import render_chart_with_expand


METRICS = ["Late %", "SLA % combined", "Avg TAT"]
GRANULARITIES = ["State", "Zone"]


def _delivered(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Current Status"] == "Delivered"]


def _month_col(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["Pickup Date"], errors="coerce").dt.to_period("M").astype(str)


def _build_pivot(df: pd.DataFrame, granularity: str, metric: str):
    delivered = _delivered(df).copy()
    if delivered.empty:
        return None, None

    delivered["_month"] = _month_col(delivered)
    row_col = "State" if granularity == "State" else "_destination_zone"
    delivered["_row"] = delivered[row_col].fillna("Unknown")

    if metric == "Late %":
        delivered["_metric_num"] = (delivered["_sla_status"] == "Late").astype(int)
        agg_num = delivered.groupby(["_row", "_month"])["_metric_num"].sum()
        agg_denom = delivered.groupby(["_row", "_month"]).size()
        value = (100 * agg_num / agg_denom).round(0)
    elif metric == "SLA % combined":
        delivered["_metric_num"] = delivered["_sla_status"].isin(["Early", "On Time"]).astype(int)
        agg_num = delivered.groupby(["_row", "_month"])["_metric_num"].sum()
        agg_denom = delivered.groupby(["_row", "_month"]).size()
        value = (100 * agg_num / agg_denom).round(0)
    else:  # Avg TAT
        agg = delivered.groupby(["_row", "_month"])["_actual_tat_days"].mean()
        value = agg.round(1)
        agg_denom = delivered.groupby(["_row", "_month"]).size()

    pivot_val = value.unstack(fill_value=np.nan)
    pivot_count = agg_denom.unstack(fill_value=0)

    totals = delivered.groupby("_row").size().sort_values(ascending=False)
    row_order = [r for r in totals.index if r in pivot_val.index]
    pivot_val = pivot_val.reindex(row_order)
    pivot_count = pivot_count.reindex(row_order)

    col_order = sorted(pivot_val.columns)
    pivot_val = pivot_val[col_order]
    pivot_count = pivot_count[col_order]

    return pivot_val, pivot_count


def render(df: pd.DataFrame, section_key: str) -> None:
    c1, c2 = st.columns(2)
    granularity = c1.selectbox(
        "Granularity",
        options=GRANULARITIES,
        key=f"heatmap_gran_{section_key}",
    )
    metric = c2.selectbox(
        "Metric",
        options=METRICS,
        key=f"heatmap_metric_{section_key}",
    )

    pivot_val, pivot_count = _build_pivot(df, granularity, metric)
    if pivot_val is None or pivot_val.empty:
        st.info("Not enough Delivered shipments to build a heatmap.")
        return

    # Build cell text.
    if metric == "Avg TAT":
        text = pivot_val.applymap(
            lambda v: "" if pd.isna(v) else f"{v:.1f} d"
        )
    else:
        text_rows = []
        for r in pivot_val.index:
            row_cells = []
            for c in pivot_val.columns:
                v = pivot_val.at[r, c]
                n = int(pivot_count.at[r, c])
                if pd.isna(v):
                    row_cells.append("")
                else:
                    row_cells.append(f"{v:.0f}% (n={n})")
            text_rows.append(row_cells)
        text = pd.DataFrame(text_rows, index=pivot_val.index, columns=pivot_val.columns)

    # Color scale per metric.
    if metric == "SLA % combined":
        # high SLA = good = yellow (high), low = dark
        colorscale = [[0, BG_BASE], [0.5, "#5A5A5F"], [1, STATUS_EARLY]]
        zmin, zmax = 0, 100
    elif metric == "Late %":
        # high Late = bad = red, low = good (yellow-tinged)
        colorscale = [[0, STATUS_EARLY], [0.5, YELLOW_PRIMARY], [1, STATUS_LATE]]
        zmin, zmax = 0, 100
    else:  # Avg TAT — single-hue dark → yellow
        colorscale = HEATMAP_COLORSCALE
        zmin = float(np.nanmin(pivot_val.values))
        zmax = float(np.nanmax(pivot_val.values))

    fig = px.imshow(
        pivot_val,
        text_auto=False,
        aspect="auto",
        color_continuous_scale=colorscale,
        zmin=zmin,
        zmax=zmax,
        labels=dict(color=metric),
    )
    fig.update_traces(
        text=text.values,
        texttemplate="%{text}",
        textfont=dict(color="#0A0A0B", family="JetBrains Mono", size=10),
        hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>",
    )
    fig = apply_plotly_defaults(fig)
    fig.update_xaxes(side="bottom", title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(
        title=dict(text=f"{granularity} × Month — {metric}", font=dict(size=13)),
        height=max(350, 30 * len(pivot_val.index) + 100),
        margin=dict(l=10, r=10, t=50, b=10),
    )

    # Stats: flatten pivot to long form for the expanded view, top 25 worst.
    long = pivot_val.reset_index().melt(
        id_vars=pivot_val.index.name or "index",
        var_name="Month",
        value_name=metric,
    ).dropna()
    if not long.empty:
        sort_asc = (metric == "SLA % combined")  # for SLA, lower is worse
        long = long.sort_values(metric, ascending=sort_asc).head(25)
        long[metric] = long[metric].round(1)

    render_chart_with_expand(
        fig,
        key=f"heatmap_{section_key}",
        title=f"Heatmap — {granularity} × Month — {metric}",
        stats_df=long if not long.empty else None,
        extra_md=f"Showing worst-performing cells (top 25 by {metric}).",
    )
