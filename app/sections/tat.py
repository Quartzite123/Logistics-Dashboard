"""Section 2 — TAT Analysis (README §13). Delivered-only spreadsheet.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section header with upload trigger.
- Table uses left-border SLA accent (no full-row tint), pill status column,
  integer-typed numeric columns.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..components import chart_pair, data_table, layout
from ..components.theme import render_section_header, get_plotly_layout
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import (
    load_latest,
    get_oda_sla_summary,
    get_oda_sla_by_company,
)


DEFAULT_VISIBLE = [
    "LRN", "Order id", "Current Status",
    "Manifest Date", "Delivered Date",
    "_oda", "_expected_tat_days", "_actual_tat_days",
    "_tat_variance_days", "_sla_status",
]

OPTIONAL_VISIBLE = [
    "Consignee name", "Additional Remarks", "No of boxes", "Weight",
    "Payment Type", "Package Amount", "Pin code",
    "_origin_zone", "_destination_zone",
]

ALL_TOGGLEABLE = DEFAULT_VISIBLE + OPTIONAL_VISIBLE

DISPLAY_LABEL = {
    "_oda": "ODA",
    "_expected_tat_days": "Expected TAT",
    "_actual_tat_days": "Actual TAT",
    "_tat_variance_days": "TAT Variance",
    "_sla_status": "SLA Status",
    "_origin_zone": "Origin Zone",
    "_destination_zone": "Destination Zone",
}


def _sla_classifier(row: pd.Series) -> Optional[str]:
    """Return one of: 'early' / 'ontime' / 'late' / None — used for left accent."""
    val = row.get("SLA Status") or row.get("_sla_status")
    if val == "Early":
        return "early"
    if val == "On Time":
        return "ontime"
    if val == "Late":
        return "late"
    return None


def render() -> None:
    upload_clicked = render_section_header("TAT Analysis", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df = load_latest()
    df = df[df["Current Status"] == "Delivered"]
    df = df[df["Manifest Date"].notna() & df["Delivered Date"].notna()]

    if df.empty:
        st.info("No Delivered shipments yet. Click ↑ Upload above to load a Delhivery file.")
        return

    # SLA filter dropdown
    sla_filter = st.selectbox(
        "SLA filter",
        options=["All", "Early", "On Time", "Late"],
        key="tat_sla_filter",
    )
    if sla_filter != "All":
        df = df[df["_sla_status"] == sla_filter]

    left, right = layout.horizontal_split(section_key="tat", default="60/40")

    if left is not None:
        with left:
            _render_table(df)

    if right is not None:
        top, bottom = layout.vertical_split(section_key="tat", container=right)
        # Top donut kept; bottom selectable chart replaced by the ODA section.
        chart_pair.render(df, section_key="tat", top_box=top, bottom_box=None)
        with bottom:
            _render_oda_performance()


def _render_table(df: pd.DataFrame) -> None:
    visible = data_table.column_picker(
        section_key="tat",
        all_columns=ALL_TOGGLEABLE,
        default_visible=DEFAULT_VISIBLE,
    )
    sort_col, ascending = data_table.sort_controls(
        section_key="tat",
        sortable_columns=visible,
        default_col="Manifest Date",
        default_dir="Desc",
    )

    rename_map = {k: v for k, v in DISPLAY_LABEL.items() if k in df.columns and k in visible}
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
        file_name=f"kiirus_tat_{datetime.now():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_tat",
    )

    data_table.render_table(
        show_df,
        visible_columns=visible_display,
        sort_col=sort_col_display,
        ascending=ascending,
        row_classifier=_sla_classifier,
    )


def _render_oda_performance() -> None:
    df_oda = get_oda_sla_summary()

    if not df_oda.empty:
        # Compute percentages within each ODA group
        totals = df_oda.groupby('oda')['count'].transform('sum')
        df_oda['pct'] = (df_oda['count'] / totals * 100).round(1)

        # Build grouped bar chart
        COLOR_MAP = {'Early':'#4ADE80','On Time':'#60A5FA','Late':'#F87171'}
        fig = go.Figure()
        for sla in ['Early','On Time','Late']:
            sub = df_oda[df_oda['sla_status']==sla].copy()
            sub['x_label'] = sub['oda'].map({'YES':'ODA','NO':'Non-ODA'})
            sub = sub.set_index('x_label').reindex(['ODA','Non-ODA'])
            fig.add_trace(go.Bar(
                name=sla,
                x=['ODA','Non-ODA'],
                y=sub['pct'].tolist(),
                text=[f"{v:.1f}%" for v in sub['pct'].tolist()],
                textposition='inside',
                insidetextanchor='middle',
                marker_color=COLOR_MAP[sla],
                marker_line_width=0,
            ))
        fig.update_layout(
            barmode='group',
            title='ODA vs Non-ODA — SLA Performance',
            yaxis_title='% of delivered orders',
            xaxis_title=None,
            bargap=0.3,
            bargroupgap=0.05,
            **get_plotly_layout()
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detail table inside expander
        with st.expander("📋 Detail breakdown — ODA vs Non-ODA by company"):
            df_co = get_oda_sla_by_company()

            # Compute percentages, avoid divide by zero
            def safe_pct(num, den):
                return (num / den * 100).round(1).where(den > 0, 0.0)

            df_co['oda_early_pct']  = safe_pct(df_co['oda_early'],  df_co['oda_total'])
            df_co['oda_ontime_pct'] = safe_pct(df_co['oda_ontime'], df_co['oda_total'])
            df_co['oda_late_pct']   = safe_pct(df_co['oda_late'],   df_co['oda_total'])
            df_co['non_early_pct']  = safe_pct(df_co['non_early'],  df_co['non_total'])
            df_co['non_ontime_pct'] = safe_pct(df_co['non_ontime'], df_co['non_total'])
            df_co['non_late_pct']   = safe_pct(df_co['non_late'],   df_co['non_total'])

            # Build display DataFrame with % strings
            display = pd.DataFrame({
                'Company':          df_co['company'],
                'ODA Early %':      df_co['oda_early_pct'].apply(lambda x: f"{x:.1f}%"),
                'ODA On Time %':    df_co['oda_ontime_pct'].apply(lambda x: f"{x:.1f}%"),
                'ODA Late %':       df_co['oda_late_pct'].apply(lambda x: f"{x:.1f}%"),
                'Non-ODA Early %':  df_co['non_early_pct'].apply(lambda x: f"{x:.1f}%"),
                'Non-ODA On Time %':df_co['non_ontime_pct'].apply(lambda x: f"{x:.1f}%"),
                'Non-ODA Late %':   df_co['non_late_pct'].apply(lambda x: f"{x:.1f}%"),
            })

            # Color config — green for Early cols, blue for OnTime, red for Late
            # Late cells also get intensity based on value
            column_config = {
                'ODA Early %':       st.column_config.TextColumn(
                    'Early %', help='ODA Early %'),
                'ODA On Time %':     st.column_config.TextColumn(
                    'On Time %', help='ODA On Time %'),
                'ODA Late %':        st.column_config.TextColumn(
                    'Late %', help='ODA Late %'),
                'Non-ODA Early %':   st.column_config.TextColumn(
                    'Early %', help='Non-ODA Early %'),
                'Non-ODA On Time %': st.column_config.TextColumn(
                    'On Time %', help='Non-ODA On Time %'),
                'Non-ODA Late %':    st.column_config.TextColumn(
                    'Late %', help='Non-ODA Late %'),
            }

            # Inject CSS to color the column headers and Late cells
            st.markdown("""
            <style>
            [data-testid="stDataFrame"] th:nth-child(2),
            [data-testid="stDataFrame"] th:nth-child(5) {
                color: #4ADE80 !important; font-weight: 600 !important;
            }
            [data-testid="stDataFrame"] th:nth-child(3),
            [data-testid="stDataFrame"] th:nth-child(6) {
                color: #60A5FA !important; font-weight: 600 !important;
            }
            [data-testid="stDataFrame"] th:nth-child(4),
            [data-testid="stDataFrame"] th:nth-child(7) {
                color: #F87171 !important; font-weight: 600 !important;
            }
            </style>
            """, unsafe_allow_html=True)

            st.dataframe(display, use_container_width=True,
                         hide_index=True, column_config=column_config)

            # Note about Late % coloring
            st.caption(
                "Late % above 25% indicates performance concern · "
                "above 40% is critical"
            )
