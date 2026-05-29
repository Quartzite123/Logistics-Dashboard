"""Click-to-expand helper for charts.

Renders any Plotly figure inline plus an `⛶ Expand` button. Clicking the
button reveals a larger version of the chart inline (with an optional stats
table) and a Close button. Session-state driven rather than @st.dialog so it
works under stlite / Pyodide, which throws "Could not find fragment with id"
for the fragment-based dialog on mobile.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_chart_with_expand(
    fig: go.Figure,
    key: str,
    title: str = "",
    stats_df: Optional[pd.DataFrame] = None,
    extra_md: Optional[str] = None,
) -> None:
    """Render a chart inline plus a small Expand button beneath it."""
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")

    expanded_key = f"_chart_expanded_{key}"

    # Small caption + expand button in the same row.
    c1, c2 = st.columns([5, 1])
    if c2.button("⛶ Expand", key=f"expand_{key}", use_container_width=True):
        st.session_state[expanded_key] = True

    if st.session_state.get(expanded_key):
        with st.container(border=True):
            if title:
                st.markdown(f"### {title}")

            # Render a larger version of the figure.
            big = go.Figure(fig)  # shallow copy
            big.update_layout(height=520, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(big, use_container_width=True, key=f"dialog_chart_{key}")

            if extra_md:
                st.markdown(extra_md)

            if stats_df is not None and not stats_df.empty:
                st.markdown("#### Breakdown")
                st.dataframe(stats_df, hide_index=True, use_container_width=True, height=300)

            if st.button("Close", key=f"close_expand_{key}", use_container_width=True):
                st.session_state[expanded_key] = False
                st.rerun()
