"""KPI card grid for the Landing page.

Builds a `rows` payload from the dataframe and hands it off to the
`kiirus_kpi_grid` custom component, which owns all the visual styling
inside its iframe. Color mapping follows the design system spec:

| Metric         | value_color |
|----------------|-------------|
| Total Orders   | primary (var(--text))           |
| Delivered      | ok (green)                      |
| In Transit     | info (blue)                     |
| Pending        | warn (amber)                    |
| RTO            | bad (red)                       |
| Date Range     | primary                         |
| Early          | ok                              |
| On Time        | info                            |
| SLA (E+OT)     | accent (yellow — compliance)    |
| Late           | bad                             |
| ODA            | warn                            |
| Non-ODA        | primary                         |
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .kpi_grid_component import render_kpi_grid


def _pct(num: int, denom: int) -> float | None:
    """Return num/denom * 100, or None if denom is zero/empty."""
    if denom <= 0:
        return None
    return 100.0 * num / denom


def _fmt_pct_of(num: int, denom: int, label: str = "of total") -> str:
    p = _pct(num, denom)
    if p is None:
        return "—"
    return f"{p:.1f}% {label}"


def _date_range(df: pd.DataFrame) -> tuple[str | None, str | None]:
    pickup = pd.to_datetime(df["Pickup Date"], errors="coerce")
    delivered_dt = pd.to_datetime(df["Delivered Date"], errors="coerce")
    all_dates = pd.concat([pickup, delivered_dt]).dropna()
    if all_dates.empty:
        return None, None
    lo, hi = all_dates.min().date(), all_dates.max().date()
    return lo.strftime("%d %b %Y"), hi.strftime("%d %b %Y")


def _fmt_n(n: int) -> str:
    return f"{n:,}"


def render(df: pd.DataFrame) -> None:
    """Render all 12 KPI cards via the iframe component."""
    total = len(df)
    if total == 0:
        st.info("No data yet — open Upload from the header above to load a Delhivery file.")
        return

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

    date_from, date_to = _date_range(df)

    rows: list[dict] = [
        # Row 1: Totals (3 cards)
        {
            "cols": 3,
            "cards": [
                {
                    "label": "Total Orders",
                    "value": _fmt_n(total),
                    "value_color": "primary",
                    "accent": True,
                    "meta": "All shipments in pipeline",
                },
                {
                    "label": "Delivered",
                    "value": _fmt_n(delivered),
                    "value_color": "ok",
                    "accent": True,
                    "meta": _fmt_pct_of(delivered, total),
                    "progress": {"value": _pct(delivered, total) or 0, "kind": "ok"},
                },
                {
                    "label": "In Transit",
                    "value": _fmt_n(in_transit),
                    "value_color": "info",
                    "accent": True,
                    "meta": _fmt_pct_of(in_transit, total),
                },
            ],
        },
        # Row 2: Status + Date (3 cards)
        {
            "cols": 3,
            "cards": [
                {
                    "label": "Pending",
                    "value": _fmt_n(pending),
                    "value_color": "warn",
                    "accent": True,
                    "meta": _fmt_pct_of(pending, total),
                },
                {
                    "label": "RTO",
                    "value": _fmt_n(rto),
                    "value_color": "bad",
                    "accent": True,
                    "meta": _fmt_pct_of(rto, total),
                },
                {
                    "label": "Date Range",
                    "value_color": "primary",
                    "accent": True,
                    "date_range": True,
                    "date_from": date_from or "—",
                    "date_to": date_to or "—",
                    "meta": "based on Pickup Date",
                },
            ],
        },
        # Row 3: SLA quad (4 cards)
        {
            "cols": 4,
            "cards": [
                {
                    "label": "Early",
                    "value": _fmt_n(early),
                    "value_color": "ok",
                    "accent": True,
                    "meta": _fmt_pct_of(early, delivered, "of delivered"),
                    "progress": {"value": _pct(early, delivered) or 0, "kind": "ok"},
                },
                {
                    "label": "On Time",
                    "value": _fmt_n(on_time),
                    "value_color": "info",
                    "accent": True,
                    "meta": _fmt_pct_of(on_time, delivered, "of delivered"),
                    "progress": {"value": _pct(on_time, delivered) or 0, "kind": "ok"},
                },
                {
                    "label": "SLA (Early + On Time)",
                    "value": _fmt_n(sla_combined),
                    "value_color": "accent",
                    "accent": True,
                    "meta": (
                        f"{_pct(sla_combined, delivered):.1f}% SLA compliance"
                        if _pct(sla_combined, delivered) is not None else "—"
                    ),
                    "progress": {"value": _pct(sla_combined, delivered) or 0},
                },
                {
                    "label": "Late",
                    "value": _fmt_n(late),
                    "value_color": "bad",
                    "accent": True,
                    "meta": _fmt_pct_of(late, delivered, "of delivered"),
                    "progress": {"value": _pct(late, delivered) or 0, "kind": "bad"},
                },
            ],
        },
        # Row 4: ODA (2 cards)
        {
            "cols": 2,
            "cards": [
                {
                    "label": "ODA · Out of delivery area",
                    "value": _fmt_n(oda_yes),
                    "value_color": "warn",
                    "accent": True,
                    "unit": "pincodes",
                    "meta": _fmt_pct_of(oda_yes, total),
                },
                {
                    "label": "Non-ODA",
                    "value": _fmt_n(oda_no),
                    "value_color": "primary",
                    "accent": True,
                    "unit": "pincodes",
                    "meta": _fmt_pct_of(oda_no, total),
                },
            ],
        },
    ]

    render_kpi_grid(
        rows=rows,
        theme=st.session_state.get("theme_mode", "dark"),
        density=st.session_state.get("density", "balanced"),
    )
