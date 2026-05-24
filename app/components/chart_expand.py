"""Click-to-expand helper for charts.

Renders any Plotly figure inline plus an `⛶ Expand` button. Clicking the
button opens a fullscreen modal (st.dialog) with the chart at large size
and an optional stats table below.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.dialog("Chart — expanded view", width="large")
def _chart_expand_dialog() -> None:
    payload = st.session_state.get("_chart_expand_payload")
    if payload is None:
        st.info("No chart loaded.")
        return

    title = payload.get("title", "")
    fig: go.Figure = payload["fig"]
    stats: Optional[pd.DataFrame] = payload.get("stats")
    extra_md: Optional[str] = payload.get("extra_md")

    if title:
        st.markdown(f"### {title}")

    # Render a larger version of the figure.
    big = go.Figure(fig)  # shallow copy
    big.update_layout(height=520, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(big, use_container_width=True, key="dialog_chart")

    if extra_md:
        st.markdown(extra_md)

    if stats is not None and not stats.empty:
        st.markdown("#### Breakdown")
        st.dataframe(stats, hide_index=True, use_container_width=True, height=300)


def render_chart_with_expand(
    fig: go.Figure,
    key: str,
    title: str = "",
    stats_df: Optional[pd.DataFrame] = None,
    extra_md: Optional[str] = None,
) -> None:
    """Render a chart inline plus a small Expand button beneath it."""
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")

    # Small caption + expand button in the same row.
    c1, c2 = st.columns([5, 1])
    if c2.button("⛶ Expand", key=f"expand_{key}", use_container_width=True):
        st.session_state["_chart_expand_payload"] = {
            "fig": fig,
            "stats": stats_df,
            "title": title or key,
            "extra_md": extra_md,
        }
        _chart_expand_dialog()
