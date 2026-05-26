"""Design tokens + Plotly layout config + small helpers.

The page-level CSS that used to live here is gone — visual styling now
lives inside the custom components (`_html/sidebar/`, `_html/kpi_grid/`),
each of which has the full `styles.css` design system inlined into its
iframe. This module retains the token dicts, the Plotly defaults, and a
few helpers that are imported by chart/data-table modules and section
files we don't touch in this redesign.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


# ---- Status colors (SAME in both themes) ---------------------------------

STATUS_EARLY   = "#4ADE80"
STATUS_ONTIME  = "#60A5FA"
STATUS_LATE    = "#F87171"
STATUS_RTO     = "#6B7280"
STATUS_PENDING = "#FBBF24"
STATUS_NA      = "#9CA3AF"


STATUS_COLORS: dict[str, str] = {
    "Early":             STATUS_EARLY,
    "On Time":           STATUS_ONTIME,
    "Late":              STATUS_LATE,
    "RTO":               STATUS_RTO,
    "Pending":           STATUS_PENDING,
    "Not Yet Delivered": STATUS_NA,
    "Manifested":        STATUS_NA,
    "Dispatched":        STATUS_ONTIME,
    "In Transit":        STATUS_ONTIME,
    "Delivered":         STATUS_EARLY,
}

STATUS_SOFT: dict[str, str] = {
    "Early":             "rgba(74, 222, 128, 0.14)",
    "On Time":           "rgba(96, 165, 250, 0.14)",
    "Late":              "rgba(248, 113, 113, 0.16)",
    "RTO":               "rgba(107, 114, 128, 0.18)",
    "Pending":           "rgba(251, 191, 36, 0.16)",
    "Not Yet Delivered": "rgba(156, 163, 175, 0.20)",
    "Manifested":        "rgba(156, 163, 175, 0.20)",
    "Dispatched":        "rgba(96, 165, 250, 0.14)",
    "In Transit":        "rgba(96, 165, 250, 0.14)",
    "Delivered":         "rgba(74, 222, 128, 0.14)",
}


# ---- Theme token dicts (mirror reference/styles.css) ---------------------

DARK = {
    "bg":            "#0b0c0d",
    "bg_elev_1":     "#131417",
    "bg_elev_2":     "#1a1c20",
    "bg_elev_3":     "#22252a",
    "sidebar_bg":    "#0e0f11",
    "border":        "#25272c",
    "border_strong": "#34373d",
    "border_hover":  "#4a4e56",
    "text":          "#f1f1f3",
    "text_muted":    "#a3a5ab",
    "text_dim":      "#6b6e75",
    "text_faint":    "#4a4d54",
    "accent":        "#f5c518",
    "accent_hover":  "#ffd633",
    "accent_soft":   "rgba(245, 197, 24, 0.14)",
    # backwards-compat keys still referenced by chart/section code:
    "bg_base":            "#0b0c0d",
    "surface_1":          "#131417",
    "surface_2":          "#1a1c20",
    "surface_3":          "#22252a",
    "border_default":     "#25272c",
    "text_primary":       "#f1f1f3",
    "yellow_primary":     "#f5c518",
    "yellow_strong":      "#ffd633",
    "yellow_soft":        "rgba(245, 197, 24, 0.14)",
    "yellow_edge":        "rgba(245, 197, 24, 0.28)",
    "yellow_glow":        "0 0 0 1px rgba(245, 197, 24, 0.35)",
    "yellow_glow_strong": "0 0 24px rgba(245, 197, 24, 0.30)",
    "footer_dot":         "#4ade80",
    "shadow_card":        "0 1px 2px rgba(0,0,0,0.4)",
    "shadow_hover":       "0 6px 20px -8px rgba(0,0,0,0.55)",
    "shadow_kpi_hover":   "0 6px 20px -8px rgba(0,0,0,0.55)",
    "transition_fast":    "all 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
    "transition_med":     "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    "sidebar_border":     "#25272c",
    "sidebar_label":      "#6b6e75",
    "sidebar_hover_bg":   "#131417",
    "sidebar_inactive_text": "#a3a5ab",
    "sidebar_inactive_sub":  "#6b6e75",
    "sidebar_icon_bg":    "rgba(255,255,255,0.04)",
    "sidebar_icon_color": "#a3a5ab",
    "input_bg":           "#1a1c20",
    "input_border":       "#34373d",
}

LIGHT = {
    "bg":            "#fafaf6",
    "bg_elev_1":     "#ffffff",
    "bg_elev_2":     "#f4f4ee",
    "bg_elev_3":     "#ebebe4",
    "sidebar_bg":    "#f4f4ee",
    "border":        "#e4e4dc",
    "border_strong": "#d0d0c6",
    "border_hover":  "#a8a89e",
    "text":          "#19191c",
    "text_muted":    "#54545a",
    "text_dim":      "#84848c",
    "text_faint":    "#b0b0b6",
    "accent":        "#c89b00",
    "accent_hover":  "#a87f00",
    "accent_soft":   "rgba(200, 155, 0, 0.12)",
    "bg_base":            "#fafaf6",
    "surface_1":          "#ffffff",
    "surface_2":          "#f4f4ee",
    "surface_3":          "#ebebe4",
    "border_default":     "#e4e4dc",
    "text_primary":       "#19191c",
    "yellow_primary":     "#c89b00",
    "yellow_strong":      "#a87f00",
    "yellow_soft":        "rgba(200, 155, 0, 0.12)",
    "yellow_edge":        "rgba(200, 155, 0, 0.32)",
    "yellow_glow":        "0 0 0 1px rgba(200, 155, 0, 0.4)",
    "yellow_glow_strong": "0 0 24px rgba(200, 155, 0, 0.18)",
    "footer_dot":         "#16a34a",
    "shadow_card":        "0 1px 2px rgba(0,0,0,0.05)",
    "shadow_hover":       "0 6px 20px -8px rgba(0,0,0,0.10)",
    "shadow_kpi_hover":   "0 6px 20px -8px rgba(0,0,0,0.10)",
    "transition_fast":    "all 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
    "transition_med":     "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    "sidebar_border":     "#e4e4dc",
    "sidebar_label":      "#84848c",
    "sidebar_hover_bg":   "#f4f4ee",
    "sidebar_inactive_text": "#54545a",
    "sidebar_inactive_sub":  "#84848c",
    "sidebar_icon_bg":    "rgba(0,0,0,0.04)",
    "sidebar_icon_color": "#54545a",
    "input_bg":           "#ffffff",
    "input_border":       "#e4e4dc",
}


def current_mode() -> str:
    return st.session_state.get("theme_mode", "dark")


def tokens() -> dict:
    return LIGHT if current_mode() == "light" else DARK


def t(key: str) -> str:
    return tokens()[key]


# ---- Session-state defaults ---------------------------------------------

def ensure_session_defaults() -> None:
    """Initialise the three values that drive the visual system."""
    st.session_state.setdefault("theme_mode", "dark")
    st.session_state.setdefault("density", "balanced")
    st.session_state.setdefault("sidebar_width", "standard")


# ---- Plotly defaults -----------------------------------------------------

SERIES_COLORS = ["#f5c518", STATUS_ONTIME, STATUS_EARLY, STATUS_LATE, STATUS_PENDING]
HEATMAP_COLORSCALE = [[0.0, "#0b0c0d"], [1.0, "#f5c518"]]


def get_plotly_layout() -> dict:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t("text_muted"), family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        colorway=[STATUS_EARLY, STATUS_ONTIME, STATUS_LATE, STATUS_PENDING, "#a3a5ab"],
        xaxis=dict(
            gridcolor=t("border"),
            zerolinecolor=t("border"),
            tickfont=dict(color=t("text_muted")),
        ),
        yaxis=dict(
            gridcolor=t("border"),
            zerolinecolor=t("border"),
            tickfont=dict(color=t("text_muted")),
        ),
        legend=dict(font=dict(color=t("text_muted"))),
    )


def apply_plotly_defaults(fig):
    fig.update_layout(**get_plotly_layout())
    fig.update_xaxes(tickfont=dict(color=t("text_muted")))
    fig.update_yaxes(tickfont=dict(color=t("text_muted")))
    return fig


# ---- Integer display helper ----------------------------------------------

INTEGER_DISPLAY_COLUMNS = {
    "_actual_tat_days", "_expected_tat_days", "_tat_variance_days",
    "Expected TAT", "Actual TAT", "TAT Variance",
    "Days in Transit",
    "LRN", "Pin code", "No of boxes", "Dispatch Count",
    "Master Waybill", "Attempt Count",
    "Total Orders", "Delivered", "In Transit", "Pending", "RTO",
}


def format_int_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if col in INTEGER_DISPLAY_COLUMNS:
            try:
                out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
            except Exception:
                pass
    return out


# ---- Section header helpers (used by section files) ---------------------

def section_title(title: str) -> None:
    st.markdown(
        f'<div style="margin-bottom:18px;">'
        f'<h1 style="margin:0; padding:0; font-size:26px; font-weight:600; '
        f'letter-spacing:-0.01em; color:{t("text")};">{title}</h1>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_section_header(title: str, show_upload_button: bool = True) -> bool:
    cols = st.columns([6, 2])
    with cols[0]:
        section_title(title)
    clicked = False
    if show_upload_button:
        with cols[1]:
            clicked = st.button(
                "↑ Upload new file(s)",
                key=f"upload_trigger_{title}",
                use_container_width=False,
            )
    return clicked


# ---- Backwards-compat constants (deprecated — prefer t(key)) -----------

BG_BASE = DARK["bg"]
SURFACE_1 = DARK["bg_elev_1"]
TEXT_PRIMARY = DARK["text"]
YELLOW_PRIMARY = DARK["accent"]
YELLOW_SOFT = DARK["accent_soft"]
PLOTLY_LAYOUT = get_plotly_layout()
