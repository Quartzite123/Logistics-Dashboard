"""Top fixed pie + bottom selectable chart (README §17.3, §17.4).

- Always-visible numbers/percentages on slices (textinfo="label+percent+value").
- Click-to-expand on every chart → modal with larger view + breakdown table.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .theme import (
    STATUS_COLORS, SERIES_COLORS,
    apply_plotly_defaults,
    t,
)
from .chart_expand import render_chart_with_expand


PIE_COLOR_MAP = {
    "Early":             STATUS_COLORS["Early"],
    "On Time":           STATUS_COLORS["On Time"],
    "Late":              STATUS_COLORS["Late"],
    "Not Yet Delivered": STATUS_COLORS["Not Yet Delivered"],
    "Manifested":        "#5A5A5F",
    "Dispatched":        "#60A5FA",
    "In Transit":        "#60A5FA",
    "Pending":           STATUS_COLORS["Pending"],
    "RTO":               STATUS_COLORS["RTO"],
    "Delivered":         STATUS_COLORS["Early"],
}


def _pie_with_stats(values: pd.Series, title: str, color_map: Optional[dict] = None):
    """Build a donut figure with always-visible slice labels + a stats DF."""
    counts = values.dropna().astype(str).value_counts()
    total = int(counts.sum())

    fig = px.pie(
        names=counts.index,
        values=counts.values,
        title=title,
        color=counts.index,
        color_discrete_map=color_map or PIE_COLOR_MAP,
        hole=0.5,
    )
    # Always-visible numbers on slices: percent inside, label outside.
    fig.update_traces(
        textinfo="percent+value",
        textposition="inside",
        insidetextorientation="horizontal",
        textfont=dict(color="#0A0A0B", family="Inter", size=12, weight="bold"),
        marker=dict(line=dict(color="#0A0A0B", width=1)),
        hovertemplate="<b>%{label}</b><br>%{value:,} shipments (%{percent})<extra></extra>",
    )
    fig = apply_plotly_defaults(fig)
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=t("text_primary"))),
        legend=dict(orientation="h", y=-0.05, font=dict(size=11)),
        height=320,
        margin=dict(l=10, r=10, t=40, b=20),
        showlegend=True,
        uniformtext=dict(minsize=10, mode="show"),
    )

    # Stats DF for the expanded view.
    stats = pd.DataFrame({
        "Category": counts.index,
        "Count":    counts.values,
        "Percent":  [f"{(100 * v / total):.1f}%" for v in counts.values],
    })
    return fig, stats, total


# --------- top-fixed-pie content per section -------------------------------

def _render_top_pie(df: pd.DataFrame, key: str, builder) -> None:
    fig, stats, total = builder(df)
    render_chart_with_expand(
        fig, key=f"top_pie_{key}", title=f"{key} — top pie",
        stats_df=stats,
        extra_md=f"**Total shipments:** {total:,}",
    )


def _builder_landing(df: pd.DataFrame):
    bucket = df["_sla_status"].copy()
    is_delivered = df["Current Status"] == "Delivered"
    bucket = bucket.where(is_delivered, "Not Yet Delivered")
    bucket = bucket.fillna("Not Yet Delivered")
    return _pie_with_stats(bucket, "Overall Delivery Performance")


def _builder_tat(df: pd.DataFrame):
    delivered = df[df["Current Status"] == "Delivered"]
    return _pie_with_stats(delivered["_sla_status"], "SLA distribution (Delivered)")


def _builder_transit(df: pd.DataFrame):
    non_delivered = df[df["Current Status"] != "Delivered"]
    return _pie_with_stats(non_delivered["Current Status"], "In-flight status distribution")


def _builder_customize(df: pd.DataFrame):
    bucket = df["_sla_status"].copy()
    is_delivered = df["Current Status"] == "Delivered"
    bucket = bucket.where(is_delivered, "Not Yet Delivered")
    bucket = bucket.fillna("Not Yet Delivered")
    return _pie_with_stats(bucket, "SLA status of filtered set")


PIE_BUILDERS = {
    "landing":   _builder_landing,
    "tat":       _builder_tat,
    "transit":   _builder_transit,
    "customize": _builder_customize,
}


# --------- bottom selectable chart -----------------------------------------

CHART_TYPES = ["Line", "Bar", "Pie"]
CHART_TYPES_WITH_HEATMAP = CHART_TYPES + ["Heatmap"]
DIMENSIONS = ["Per-company", "Per-region", "Month-on-month", "By status"]


def _dimension_frame(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    if dim == "Per-company":
        agg = df.groupby(df["Order id"].fillna("Unknown")).size().reset_index(name="Count")
        agg.columns = ["Company", "Count"]
        return agg.sort_values("Count", ascending=False).head(25)
    if dim == "Per-region":
        agg = df.groupby(df["_destination_zone"].fillna("Unknown")).size().reset_index(name="Count")
        agg.columns = ["Destination Zone", "Count"]
        return agg.sort_values("Count", ascending=False)
    if dim == "Month-on-month":
        pickup = pd.to_datetime(df["Pickup Date"], errors="coerce")
        month = pickup.dt.to_period("M").astype(str)
        agg = df.assign(_month=month).groupby("_month").size().reset_index(name="Count")
        agg.columns = ["Month", "Count"]
        return agg.sort_values("Month")
    if dim == "By status":
        agg = df.groupby(df["Current Status"].fillna("Unknown")).size().reset_index(name="Count")
        agg.columns = ["Status", "Count"]
        return agg.sort_values("Count", ascending=False)
    raise ValueError(f"Unknown dimension {dim!r}")


def bottom_selectable(df: pd.DataFrame, section_key: str, allow_heatmap: bool = False) -> None:
    chart_options = CHART_TYPES_WITH_HEATMAP if allow_heatmap else CHART_TYPES
    col_t, col_d = st.columns(2)
    chart_type = col_t.selectbox(
        "Chart type",
        options=chart_options,
        key=f"chart_type_{section_key}",
    )
    if chart_type == "Heatmap":
        from .chart_heatmap import render as render_heatmap
        col_d.empty()
        render_heatmap(df, section_key)
        return

    dim = col_d.selectbox(
        "Dimension",
        options=DIMENSIONS,
        key=f"chart_dim_{section_key}",
    )

    if df.empty:
        st.info("No data to plot.")
        return

    agg = _dimension_frame(df, dim)
    if agg.empty:
        st.info(f"No data in dimension '{dim}'.")
        return

    x_col, y_col = agg.columns[0], agg.columns[1]
    title = f"{dim} — count"
    if chart_type == "Bar":
        fig = px.bar(agg, x=x_col, y=y_col, title=title,
                     color_discrete_sequence=SERIES_COLORS,
                     text=y_col)
        fig.update_traces(
            textposition="outside",
            textfont=dict(size=11, color=t("text_primary")),
            cliponaxis=False,
        )
    elif chart_type == "Line":
        fig = px.line(agg, x=x_col, y=y_col, markers=True, title=title,
                      color_discrete_sequence=SERIES_COLORS,
                      text=y_col)
        fig.update_traces(
            textposition="top center",
            textfont=dict(size=11, color=t("text_primary")),
        )
    else:  # Pie
        fig = px.pie(agg, names=x_col, values=y_col, hole=0.5, title=title,
                     color_discrete_sequence=SERIES_COLORS)
        fig.update_traces(
            textinfo="percent+value",
            textposition="inside",
            textfont=dict(color="#0A0A0B", family="Inter", size=12, weight="bold"),
            marker=dict(line=dict(color="#0A0A0B", width=1)),
            hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
        )

    fig = apply_plotly_defaults(fig)
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", y=-0.15),
        title=dict(font=dict(size=13)),
    )

    # Stats DF
    total = int(agg[y_col].sum()) if not agg.empty else 0
    stats = agg.copy()
    if total > 0:
        stats["Percent"] = [f"{(100 * v / total):.1f}%" for v in agg[y_col]]

    render_chart_with_expand(
        fig,
        key=f"bottom_{section_key}",
        title=f"{section_key} — {title}",
        stats_df=stats,
        extra_md=f"**Total:** {total:,}",
    )


def render(
    df: pd.DataFrame,
    section_key: str,
    top_box,
    bottom_box,
    allow_heatmap: bool = False,
) -> None:
    if top_box is not None:
        with top_box:
            builder = PIE_BUILDERS.get(section_key, _builder_landing)
            try:
                _render_top_pie(df, section_key, builder)
            except Exception as e:
                st.warning(f"Top pie failed: {e}")

    if bottom_box is not None:
        with bottom_box:
            bottom_selectable(df, section_key=section_key, allow_heatmap=allow_heatmap)
