"""Design tokens + global stylesheet + Plotly layout config.

Centralised theme system. Black + yellow premium aesthetic inspired by
modern AI SaaS dashboards (Linear / Vercel / Notion).

Two themes — dark (default) and light. Tokens cover surfaces, borders,
text, accent, status, plus motion (transitions), radii, and shadows.

Components consume tokens via:
    t("surface_1") / t("yellow_primary") / etc.
The CSS string is regenerated on each rerun from the active token set,
so changing st.session_state["theme_mode"] flips the entire UI.
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


# ---- Theme tokens --------------------------------------------------------

DARK = {
    # surfaces
    "bg_base":            "#070708",
    "surface_1":          "#121214",
    "surface_2":          "#18181B",
    "surface_3":          "#22222A",
    "sidebar_bg":         "#0C0C0E",
    # borders
    "border_default":     "#26262B",
    "border_strong":      "#3A3A40",
    "sidebar_border":     "#26262B",
    # text
    "text_primary":       "#F5F5F7",
    "text_muted":         "#9CA3AF",
    "text_dim":           "#6B7280",
    "sidebar_label":      "#6B7280",
    "sidebar_inactive_text":  "#D4D4D8",
    "sidebar_inactive_sub":   "#71717A",
    "sidebar_icon_bg":    "rgba(255,255,255,0.04)",
    "sidebar_icon_color": "#9CA3AF",
    "sidebar_hover_bg":   "#18181B",
    # accent (yellow)
    "yellow_primary":     "#FFD60A",
    "yellow_strong":      "#FFE03A",
    "yellow_soft":        "rgba(255, 214, 10, 0.10)",
    "yellow_edge":        "rgba(255, 214, 10, 0.28)",
    "yellow_glow":        "0 0 12px rgba(255, 214, 10, 0.45)",
    "yellow_glow_strong": "0 0 24px rgba(255, 214, 10, 0.30), 0 0 6px rgba(255, 214, 10, 0.4)",
    # status footer dot
    "footer_dot":         "#4ADE80",
    # shadow + motion
    "shadow_card":        "0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.02), inset 0 1px 0 rgba(255,255,255,0.03)",
    "shadow_hover":       "0 6px 24px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,214,10,0.20), inset 0 1px 0 rgba(255,214,10,0.06)",
    "shadow_kpi_hover":   "0 4px 16px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,214,10,0.18)",
    "transition_fast":    "all 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
    "transition_med":     "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    # input
    "input_bg":           "#1A1A1F",
    "input_border":       "#2A2A2E",
}

LIGHT = {
    "bg_base":            "#FAFAFA",
    "surface_1":          "#FFFFFF",
    "surface_2":          "#F4F4F5",
    "surface_3":          "#E4E4E7",
    "sidebar_bg":         "#FFFFFF",
    "border_default":     "#E4E4E7",
    "border_strong":      "#A1A1AA",
    "sidebar_border":     "#E4E4E7",
    "text_primary":       "#18181B",
    "text_muted":         "#52525B",
    "text_dim":           "#71717A",
    "sidebar_label":      "#71717A",
    "sidebar_inactive_text":  "#27272A",
    "sidebar_inactive_sub":   "#71717A",
    "sidebar_icon_bg":    "rgba(0,0,0,0.04)",
    "sidebar_icon_color": "#52525B",
    "sidebar_hover_bg":   "#F4F4F5",
    "yellow_primary":     "#A87E0F",
    "yellow_strong":      "#8A6909",
    "yellow_soft":        "rgba(168, 126, 15, 0.10)",
    "yellow_edge":        "rgba(168, 126, 15, 0.32)",
    "yellow_glow":        "0 0 12px rgba(168, 126, 15, 0.30)",
    "yellow_glow_strong": "0 0 24px rgba(168, 126, 15, 0.18), 0 0 6px rgba(168, 126, 15, 0.30)",
    "footer_dot":         "#16A34A",
    "shadow_card":        "0 1px 2px rgba(24,24,27,0.05), 0 0 0 1px rgba(24,24,27,0.04)",
    "shadow_hover":       "0 8px 28px rgba(168,126,15,0.12), 0 0 0 1px rgba(168,126,15,0.22)",
    "shadow_kpi_hover":   "0 4px 16px rgba(24,24,27,0.08), 0 0 0 1px rgba(168,126,15,0.20)",
    "transition_fast":    "all 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
    "transition_med":     "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    "input_bg":           "#FFFFFF",
    "input_border":       "#E4E4E7",
}


def current_mode() -> str:
    return st.session_state.get("theme_mode", "dark")


def tokens() -> dict:
    return LIGHT if current_mode() == "light" else DARK


def t(key: str) -> str:
    return tokens()[key]


# ---- Plotly layout -------------------------------------------------------

SERIES_COLORS = ["#FFD60A", STATUS_ONTIME, STATUS_EARLY, STATUS_LATE, STATUS_PENDING]
HEATMAP_COLORSCALE = [[0.0, "#0A0A0B"], [1.0, "#FFD60A"]]


def get_plotly_layout() -> dict:
    return dict(
        paper_bgcolor=t("surface_1"),
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t("text_primary"), family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(
            gridcolor=t("border_default"),
            zerolinecolor=t("border_default"),
            tickfont=dict(color=t("text_primary")),
        ),
        yaxis=dict(
            gridcolor=t("border_default"),
            zerolinecolor=t("border_default"),
            tickfont=dict(color=t("text_primary")),
        ),
        legend=dict(font=dict(color=t("text_primary"))),
    )


def apply_plotly_defaults(fig):
    fig.update_layout(**get_plotly_layout())
    fig.update_xaxes(tickfont=dict(color=t("text_primary")))
    fig.update_yaxes(tickfont=dict(color=t("text_primary")))
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


# ---- Global stylesheet ---------------------------------------------------

def _build_css(tk: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ---- CSS variables ---------------------------------------------------- */
:root, .stApp, [data-testid="stApp"] {{
  --bg-base: {tk['bg_base']};
  --surface-1: {tk['surface_1']};
  --surface-2: {tk['surface_2']};
  --surface-3: {tk['surface_3']};
  --border-default: {tk['border_default']};
  --border-strong: {tk['border_strong']};
  --text-primary: {tk['text_primary']};
  --text-muted: {tk['text_muted']};
  --text-dim: {tk['text_dim']};
  --yellow-primary: {tk['yellow_primary']};
  --yellow-strong: {tk['yellow_strong']};
  --yellow-soft: {tk['yellow_soft']};
  --yellow-edge: {tk['yellow_edge']};
  --yellow-glow: {tk['yellow_glow']};
  --shadow-card: {tk['shadow_card']};
  --shadow-hover: {tk['shadow_hover']};
  --transition-fast: {tk['transition_fast']};
  --transition-med: {tk['transition_med']};
  --status-early: {STATUS_EARLY};
  --status-ontime: {STATUS_ONTIME};
  --status-late: {STATUS_LATE};
  --status-pending: {STATUS_PENDING};
  --status-rto: {STATUS_RTO};
  /* Streamlit's own theme variables */
  --background-color: {tk['bg_base']};
  --secondary-background-color: {tk['surface_1']};
  --text-color: {tk['text_primary']};
  --primary-color: {tk['yellow_primary']};
  --font: "Inter", system-ui, sans-serif;
}}

* {{
  scrollbar-color: {tk['border_strong']} transparent;
  scrollbar-width: thin;
}}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
  background: {tk['border_default']};
  border-radius: 5px;
}}
::-webkit-scrollbar-thumb:hover {{ background: {tk['border_strong']}; }}

/* ---- App shell — every background-bearing element -------------------- */
html, body,
.stApp,
div[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section[data-testid="stMain"],
section.main,
.main,
.main > div,
[data-testid="stHeader"],
[data-testid="stBottom"] {{
  background-color: {tk['bg_base']} !important;
  color: {tk['text_primary']} !important;
  font-family: Inter, system-ui, sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}}
[data-testid="stHeader"] {{
  background: {tk['bg_base']} !important;
  border-bottom: 1px solid {tk['border_default']};
}}

/* Full-width main content with comfortable padding. */
.block-container {{
  max-width: 100% !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
}}
.main .block-container,
[data-testid="stMain"] .block-container,
[data-testid="stMainBlockContainer"] {{
  padding-top: 1.5rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
  padding-bottom: 2rem !important;
  max-width: 100% !important;
  width: 100% !important;
}}

/* ---- Typography ------------------------------------------------------- */
.stApp h1, [data-testid="stMain"] h1 {{ font-size: 28px !important; font-weight: 700 !important; letter-spacing: -0.025em !important; color: {tk['text_primary']} !important; }}
.stApp h2, [data-testid="stMain"] h2 {{ font-size: 22px !important; font-weight: 700 !important; letter-spacing: -0.02em !important; color: {tk['text_primary']} !important; }}
.stApp h3, [data-testid="stMain"] h3 {{ font-size: 17px !important; font-weight: 600 !important; letter-spacing: -0.015em !important; color: {tk['text_primary']} !important; }}
.stApp h4, [data-testid="stMain"] h4 {{ font-size: 14px !important; font-weight: 600 !important; color: {tk['text_primary']} !important; }}

.stMarkdown, .stMarkdown p, .stMarkdown li,
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{
  color: {tk['text_primary']};
  line-height: 1.55;
}}
[data-testid="stCaptionContainer"],
.stCaption {{
  color: {tk['text_muted']} !important;
  font-size: 12.5px !important;
}}
label, .stTextInput label, .stSelectbox label, .stMultiSelect label,
.stDateInput label, .stCheckbox label, .stRadio label,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p {{
  color: {tk['text_primary']} !important;
  font-weight: 500 !important;
}}

.section-title {{
  text-transform: uppercase;
  font-weight: 700;
  font-size: 11px;
  margin: 0 0 6px 0;
  letter-spacing: 0.12em;
  color: {tk['text_muted']};
}}
.section-title-accent {{
  width: 36px;
  height: 3px;
  background: linear-gradient(90deg, {tk['yellow_primary']}, {tk['yellow_strong']});
  margin: 0 0 22px 0;
  border-radius: 2px;
  box-shadow: {tk['yellow_glow']};
}}

/* ---- Sidebar --------------------------------------------------------- */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"] {{
  background: {tk['sidebar_bg']} !important;
  border-right: 1px solid {tk['sidebar_border']};
  transition: background-color 0.3s ease;
}}
[data-testid="stSidebar"] {{
  min-width: 260px !important;
  max-width: 260px !important;
  width: 260px !important;
}}
[data-testid="stSidebar"] > div:first-child {{
  padding: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] label,
[data-testid="stSidebar"] [data-testid="stToggle"] label p {{
  color: {tk['text_primary']} !important;
  font-weight: 500 !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] {{
  padding: 4px 16px 8px 16px;
}}

/* Sidebar nav buttons (inactive rows) — multi-line label support. */
[data-testid="stSidebar"] .stButton {{
  margin: 2px 8px !important;
}}
[data-testid="stSidebar"] .stButton > button {{
  background: transparent !important;
  border: 1px solid transparent !important;
  color: {tk['sidebar_inactive_text']} !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 10px 14px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  width: 100% !important;
  border-radius: 10px !important;
  height: auto !important;
  min-height: 56px !important;
  line-height: 1.35 !important;
  transition: {tk['transition_fast']};
  white-space: pre-line !important;
  letter-spacing: -0.01em;
}}
[data-testid="stSidebar"] .stButton > button > div,
[data-testid="stSidebar"] .stButton > button > div > p {{
  white-space: pre-line !important;
  text-align: left !important;
  width: 100% !important;
  margin: 0 !important;
  color: inherit !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: {tk['sidebar_hover_bg']} !important;
  color: {tk['text_primary']} !important;
  border-color: {tk['border_default']} !important;
  transform: translateX(2px);
}}
[data-testid="stSidebar"] .stButton > button:focus {{
  box-shadow: none !important;
  outline: none !important;
}}

/* ---- Sidebar nav (custom HTML anchors) ------------------------------- */
.nav-list {{
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}}
.nav-row {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid transparent;
  text-decoration: none !important;
  color: {tk['sidebar_inactive_text']} !important;
  transition: {tk['transition_fast']};
  min-height: 60px;
  position: relative;
  cursor: pointer;
}}
.nav-row:hover {{
  background: {tk['sidebar_hover_bg']};
  border-color: {tk['border_default']};
  color: {tk['text_primary']} !important;
  transform: translateX(2px);
}}
.nav-row.active {{
  background: {tk['yellow_soft']};
  border-color: {tk['yellow_edge']};
  box-shadow: inset 0 0 12px rgba(255, 214, 10, 0.04);
}}
.nav-icon {{
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  background: {tk['sidebar_icon_bg']};
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: {tk['sidebar_icon_color']};
  font-size: 18px;
  font-weight: 600;
  transition: {tk['transition_fast']};
}}
.nav-row:hover .nav-icon {{
  background: {tk['yellow_soft']};
  color: {tk['yellow_primary']};
}}
.nav-row.active .nav-icon {{
  background: {tk['yellow_soft']};
  border: 1px solid {tk['yellow_edge']};
  color: {tk['yellow_primary']};
  box-shadow: {tk['yellow_glow']};
}}
.nav-text {{
  flex: 1;
  min-width: 0;
}}
.nav-label {{
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  color: {tk['sidebar_inactive_text']};
  text-decoration: none !important;
  letter-spacing: -0.01em;
}}
.nav-row:hover .nav-label {{ color: {tk['text_primary']}; }}
.nav-row.active .nav-label {{ color: {tk['yellow_primary']}; }}
.nav-sub {{
  font-size: 11px;
  line-height: 1.4;
  margin-top: 3px;
  color: {tk['sidebar_inactive_sub']};
  letter-spacing: 0.01em;
}}
.nav-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {tk['yellow_primary']};
  box-shadow: {tk['yellow_glow_strong']};
  flex: 0 0 8px;
}}

.brand-block {{
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 22px 18px 20px 18px;
}}
.brand-icon-box {{
  width: 42px;
  height: 42px;
  background: {tk['yellow_soft']};
  border: 1px solid {tk['yellow_edge']};
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: {tk['yellow_primary']};
  font-size: 22px;
  font-weight: 700;
  flex: 0 0 42px;
  box-shadow: {tk['yellow_glow']};
}}
.brand-name {{
  font-size: 16.5px;
  font-weight: 700;
  color: {tk['text_primary']};
  letter-spacing: -0.015em;
  line-height: 1.2;
}}
.brand-tagline {{
  font-size: 9.5px;
  color: {tk['text_muted']};
  text-transform: uppercase;
  letter-spacing: 0.14em;
  margin-top: 4px;
  line-height: 1.4;
  font-weight: 500;
}}
.sidebar-section-label {{
  padding: 22px 18px 10px 18px;
  font-size: 10.5px;
  color: {tk['sidebar_label']};
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-weight: 700;
}}
.sidebar-divider {{
  height: 1px;
  background: {tk['sidebar_border']};
  margin: 0 18px;
}}
.sidebar-divider-mid {{
  height: 1px;
  background: {tk['sidebar_border']};
  margin: 14px 18px 4px 18px;
}}
.sidebar-footer {{
  padding: 16px 18px 20px 18px;
}}
.sidebar-footer-line {{
  font-size: 10.5px;
  color: {tk['sidebar_label']};
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  letter-spacing: 0.02em;
}}
.sidebar-footer-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: {tk['footer_dot']};
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.5);
}}

/* ---- KPI cards ------------------------------------------------------- */
.kpi-card {{
  background: {tk['surface_1']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 12px !important;
  padding: 18px 20px !important;
  min-height: 108px !important;
  box-shadow: {tk['shadow_card']};
  transition: {tk['transition_fast']};
  position: relative;
}}
.kpi-card:hover {{
  border-color: {tk['yellow_edge']} !important;
  box-shadow: {tk['shadow_kpi_hover']};
  transform: translateY(-1px);
}}

/* ---- Buttons --------------------------------------------------------- */
[data-testid="stMain"] .stButton > button[kind="primary"] {{
  background: {tk['yellow_primary']} !important;
  color: #0A0A0B !important;
  border: none !important;
  height: 38px !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 13.5px !important;
  letter-spacing: -0.005em !important;
  transition: {tk['transition_fast']};
  box-shadow: 0 1px 0 rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.15);
}}
[data-testid="stMain"] .stButton > button[kind="primary"]:hover {{
  background: {tk['yellow_strong']} !important;
  box-shadow: {tk['yellow_glow']};
  transform: translateY(-1px);
}}
[data-testid="stMain"] .stButton > button[kind="secondary"],
[data-testid="stMain"] .stDownloadButton > button {{
  background: {tk['surface_1']} !important;
  color: {tk['text_primary']} !important;
  border: 1px solid {tk['border_default']} !important;
  height: 38px !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: 13.5px !important;
  transition: {tk['transition_fast']};
}}
[data-testid="stMain"] .stButton > button[kind="secondary"]:hover,
[data-testid="stMain"] .stDownloadButton > button:hover {{
  background: {tk['surface_2']} !important;
  border-color: {tk['border_strong']} !important;
  color: {tk['text_primary']} !important;
}}

/* ---- Inputs --------------------------------------------------------- */
[data-baseweb="input"] input,
[data-baseweb="select"] > div,
[data-baseweb="textarea"] textarea {{
  background: {tk['input_bg']} !important;
  border: 1px solid {tk['input_border']} !important;
  color: {tk['text_primary']} !important;
  border-radius: 8px !important;
  transition: {tk['transition_fast']};
}}
[data-baseweb="input"]:focus-within input,
[data-baseweb="select"]:focus-within > div,
[data-baseweb="textarea"]:focus-within textarea {{
  border-color: {tk['yellow_primary']} !important;
  box-shadow: 0 0 0 3px {tk['yellow_soft']};
}}
[data-baseweb="select"] [role="listbox"],
[data-baseweb="popover"], [data-baseweb="popover"] > div {{
  background: {tk['surface_1']} !important;
  color: {tk['text_primary']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 8px !important;
}}
[data-baseweb="select"] [role="option"] {{
  color: {tk['text_primary']} !important;
}}
[data-baseweb="select"] [role="option"]:hover {{
  background: {tk['yellow_soft']} !important;
  color: {tk['yellow_primary']} !important;
}}

/* ---- Segmented control ---------------------------------------------- */
[data-testid="stSegmentedControl"] button {{
  background: {tk['surface_1']} !important;
  color: {tk['text_muted']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 8px !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  transition: {tk['transition_fast']};
}}
[data-testid="stSegmentedControl"] button:hover {{
  background: {tk['surface_2']} !important;
  color: {tk['text_primary']} !important;
}}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
  background: {tk['yellow_soft']} !important;
  color: {tk['yellow_primary']} !important;
  border-color: {tk['yellow_edge']} !important;
  box-shadow: {tk['yellow_glow']};
}}

/* ---- Dataframe ------------------------------------------------------- */
[data-testid="stDataFrame"] {{
  background: {tk['surface_1']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: {tk['shadow_card']};
}}

/* ---- Plotly chart container (was rendering as white box in dark mode) */
[data-testid="stPlotlyChart"] {{
  background: {tk['surface_1']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 12px !important;
  padding: 8px !important;
  margin: 4px 0 !important;
  box-shadow: {tk['shadow_card']};
  transition: {tk['transition_fast']};
}}
[data-testid="stPlotlyChart"]:hover {{
  border-color: {tk['border_strong']} !important;
}}

/* Plotly modebar — make icons visible on dark bg */
.modebar-container .modebar {{
  background: transparent !important;
}}
.modebar-btn path {{ fill: {tk['text_muted']} !important; }}
.modebar-btn:hover path {{ fill: {tk['yellow_primary']} !important; }}

/* ---- Expander ------------------------------------------------------- */
[data-testid="stExpander"],
[data-testid="stExpander"] details {{
  background: {tk['surface_1']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 12px !important;
  box-shadow: {tk['shadow_card']};
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] details > summary {{
  background: {tk['surface_1']} !important;
  color: {tk['text_primary']} !important;
  padding: 12px 16px !important;
  border-radius: 12px !important;
  font-weight: 500;
}}
[data-testid="stExpander"] summary:hover {{
  background: {tk['surface_2']} !important;
}}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"],
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {{
  color: {tk['text_primary']} !important;
}}

/* ---- Tabs ----------------------------------------------------------- */
[data-baseweb="tab-list"] {{
  background: transparent !important;
  border-bottom: 1px solid {tk['border_default']};
  gap: 4px;
}}
[data-baseweb="tab"] {{
  color: {tk['text_muted']} !important;
  font-weight: 500 !important;
  padding: 10px 16px !important;
  border-radius: 8px 8px 0 0 !important;
  transition: {tk['transition_fast']};
}}
[data-baseweb="tab"]:hover {{ color: {tk['text_primary']} !important; }}
[data-baseweb="tab"][aria-selected="true"] {{ color: {tk['yellow_primary']} !important; }}
[data-baseweb="tab-highlight"] {{
  background: {tk['yellow_primary']} !important;
  height: 2px !important;
}}

/* ---- Dialog / modals ------------------------------------------------ */
[data-testid="stDialog"],
[data-testid="stDialog"] > div {{
  background: {tk['surface_1']} !important;
  color: {tk['text_primary']} !important;
  border: 1px solid {tk['border_default']} !important;
  border-radius: 14px !important;
  box-shadow: {tk['shadow_hover']};
}}

/* ---- Alerts --------------------------------------------------------- */
[data-testid="stAlert"] {{
  border-radius: 10px !important;
  border: 1px solid {tk['border_default']} !important;
  background: {tk['surface_1']} !important;
  color: {tk['text_primary']} !important;
  padding: 12px 16px !important;
}}

/* ---- Draft banner --------------------------------------------------- */
.draft-banner {{
  padding: 12px 16px;
  border-radius: 10px;
  background: {tk['yellow_soft']};
  border: 1px solid {tk['yellow_edge']};
  color: {tk['yellow_primary']};
  font-weight: 500;
  margin: 0 0 16px 0;
  box-shadow: {tk['yellow_glow']};
}}

/* ---- Toggle (st.toggle) ---------------------------------------------- */
[data-testid="stToggle"] [data-baseweb="checkbox"] [role="checkbox"] {{
  background: {tk['surface_3']} !important;
}}
[data-testid="stToggle"] [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] {{
  background: {tk['yellow_primary']} !important;
}}
</style>
"""


def inject_global_css() -> None:
    """Inject CSS for the current theme. Safe to call on every rerun."""
    st.markdown(_build_css(tokens()), unsafe_allow_html=True)


def section_title(title: str) -> None:
    st.markdown(
        f'<div style="margin-bottom:18px;">'
        f'<h1 style="margin:0; padding:0; font-size:28px; font-weight:700; '
        f'letter-spacing:-0.025em; color:{t("text_primary")};">{title}</h1>'
        f'<div class="section-title-accent" style="margin-top:8px;"></div>'
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


# Backwards-compat constants (deprecated — prefer t(key)).
BG_BASE = DARK["bg_base"]
SURFACE_1 = DARK["surface_1"]
TEXT_PRIMARY = DARK["text_primary"]
YELLOW_PRIMARY = DARK["yellow_primary"]
YELLOW_SOFT = DARK["yellow_soft"]
PLOTLY_LAYOUT = get_plotly_layout()
