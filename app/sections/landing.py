"""Section 1 — Landing page (README §12, with the spec revision from
CLAUDE_CODE_UI_PROMPT.md).

NEW layout:
- KPI cards (4 rows: 3 / 3 / 4 / 2) span full width on top.
- Below the cards: a vertically-stacked chart pair — top fixed pie
  (Overall Delivery Performance) above a bottom selectable chart.
- The Upload widget is NO LONGER on this page. It opens via the
  '↑ Upload new file(s)' button in the section header.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..components import kpi_cards, chart_pair
from ..components.theme import render_section_header, get_plotly_layout
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest, get_monthly_trend


def render() -> None:
    upload_clicked = render_section_header("Landing", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df = load_latest()
    kpi_cards.render(df)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Donut only (Overall Delivery Performance) — bottom selectable chart removed.
    top = st.container()
    chart_pair.render(df, section_key="landing", top_box=top, bottom_box=None)

    # Month-on-Month trend chart (replaces the old bottom line chart).
    df_trend = get_monthly_trend()
    if not df_trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['total_orders'],
            name='Total Orders', mode='lines+markers+text',
            line=dict(color='#60A5FA', width=2),
            fill='tozeroy',
            fillcolor='rgba(96,165,250,0.1)',
            text=df_trend['total_orders'],
            textposition='top center',
            textfont=dict(size=11)
        ))
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['early'],
            name='Early', mode='lines+markers',
            line=dict(color='#4ADE80', width=2, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['on_time'],
            name='On Time', mode='lines+markers',
            line=dict(color='#A78BFA', width=2, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=df_trend['month'], y=df_trend['late'],
            name='Late', mode='lines+markers+text',
            line=dict(color='#F87171', width=2, dash='dash'),
            text=df_trend['late'],
            textposition='top center',
            textfont=dict(size=11)
        ))
        # Merge the category x-axis into the themed layout so months render as
        # 4 clean ticks ('Nov 2025'...) instead of weekly date ticks. Merging
        # avoids a duplicate 'xaxis' kwarg (get_plotly_layout already sets one).
        layout = get_plotly_layout()
        layout['xaxis'] = {
            **layout.get('xaxis', {}),
            'type': 'category',
            'tickvals': df_trend['month'].tolist(),
            'ticktext': [
                pd.to_datetime(m + '-01').strftime('%b %Y')
                for m in df_trend['month'].tolist()
            ],
        }
        fig.update_layout(
            title='Month on Month Order Volume & Delivery Trend',
            yaxis_title='Number of Orders',
            xaxis_title=None,
            **layout
        )
        st.plotly_chart(fig, use_container_width=True)
