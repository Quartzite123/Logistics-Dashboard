"""KPI card grid for the Landing page (README §12.2 / §12.3).

Uses literal color values resolved at render time via `t()` instead of CSS
`var()` references — Streamlit's nested DOM sometimes breaks CSS variable
inheritance for inline styles, which caused borders to be invisible. With
literal hex/rgba values, every card is unambiguously bordered.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from .theme import t


def _styles() -> dict:
    """Resolve mode-aware style strings once per render."""
    return {
        "card": (
            f"background: {t('surface_1')};"
            f" border: 1px solid {t('border_default')};"
            " border-radius: 12px;"
            " padding: 18px 20px;"
            " min-height: 108px;"
            f" box-shadow: {t('shadow_card')};"
            f" transition: {t('transition_fast')};"
        ),
        "label": (
            "font-size: 11px;"
            " text-transform: uppercase;"
            " letter-spacing: 0.10em;"
            f" color: {t('text_muted')};"
            " font-weight: 600;"
            " margin-bottom: 8px;"
            " font-family: Inter, sans-serif;"
        ),
        "value": (
            "font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace;"
            " font-size: 32px;"
            " font-weight: 700;"
            f" color: {t('yellow_primary')};"
            " line-height: 1.1;"
            " font-variant-numeric: tabular-nums;"
            " letter-spacing: -0.02em;"
        ),
        "value_date": (
            "font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace;"
            " font-size: 15px;"
            " font-weight: 600;"
            f" color: {t('text_primary')};"
            " line-height: 1.3;"
            " padding-top: 4px;"
            " letter-spacing: -0.01em;"
        ),
        "sub": (
            "font-size: 12px;"
            f" color: {t('text_muted')};"
            " margin-top: 8px;"
            " min-height: 14px;"
            " font-weight: 500;"
        ),
    }


def _fmt_pct(num: int, denom: int) -> str:
    if denom <= 0:
        return "—"
    return f"{(100 * num / denom):.1f}% of {denom:,}"


def _card(col, styles: dict, label: str, value: str, sub: Optional[str] = None, is_date: bool = False) -> None:
    value_style = styles["value_date"] if is_date else styles["value"]
    with col:
        st.markdown(
            f"""<div class="kpi-card" style="{styles['card']}">
                <div style="{styles['label']}">{label}</div>
                <div style="{value_style}">{value}</div>
                <div style="{styles['sub']}">{sub or ''}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render(df: pd.DataFrame) -> None:
    """Render all 12 KPI cards in 4 rows (3 / 3 / 4 / 2)."""
    total = len(df)
    if total == 0:
        st.info("No data yet — open Upload from the header above to load a Delhivery file.")
        return

    s = _styles()

    cs = df["Current Status"].fillna("")
    delivered = int((cs == "Delivered").sum())
    in_transit = int((cs == "In Transit").sum())
    pending = int((cs == "Pending").sum())
    rto = int((cs == "RTO").sum())

    sla = df["_sla_status"].fillna("")
    early = int((sla == "Early").sum())
    on_time = int((sla == "On Time").sum())
    late = int((sla == "Late").sum())
    sla_combined = early + on_time

    oda_col = df["_oda"].fillna("UNKNOWN")
    oda_yes = int((oda_col == "YES").sum())
    oda_no = int((oda_col == "NO").sum())

    pickup = pd.to_datetime(df["Pickup Date"], errors="coerce")
    delivered_dt = pd.to_datetime(df["Delivered Date"], errors="coerce")
    all_dates = pd.concat([pickup, delivered_dt]).dropna()
    if not all_dates.empty:
        date_min, date_max = all_dates.min().date(), all_dates.max().date()
        date_range = f"{date_min:%d-%b-%y}  →  {date_max:%d-%b-%y}"
    else:
        date_range = "—"

    c1, c2, c3 = st.columns(3, gap="medium")
    _card(c1, s, "Total Orders", f"{total:,}", "all shipments")
    _card(c2, s, "Delivered", f"{delivered:,}", _fmt_pct(delivered, total))
    _card(c3, s, "In Transit", f"{in_transit:,}", _fmt_pct(in_transit, total))

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3, gap="medium")
    _card(c4, s, "Pending", f"{pending:,}", _fmt_pct(pending, total))
    _card(c5, s, "RTO", f"{rto:,}", _fmt_pct(rto, total))
    _card(c6, s, "Date Range", date_range, "based on Pickup Date", is_date=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    c7, c8, c9, c10 = st.columns(4, gap="medium")
    _card(c7, s, "Early", f"{early:,}", _fmt_pct(early, delivered))
    _card(c8, s, "On Time", f"{on_time:,}", _fmt_pct(on_time, delivered))
    _card(c9, s, "SLA (Early+OnTime)", f"{sla_combined:,}", _fmt_pct(sla_combined, delivered))
    _card(c10, s, "Late", f"{late:,}", _fmt_pct(late, delivered))

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    c11, c12 = st.columns(2, gap="medium")
    _card(c11, s, "ODA", f"{oda_yes:,}", _fmt_pct(oda_yes, total))
    _card(c12, s, "Non-ODA", f"{oda_no:,}", _fmt_pct(oda_no, total))
