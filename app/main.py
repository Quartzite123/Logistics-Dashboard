"""Kiirus Xpress dashboard — Streamlit entry point.

Run locally:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from app.store.db import init_db
from app.store.seed import seed_all_if_empty
from app.sections import landing, tat, transit, customize, edit
from app.components.theme import inject_global_css, t


# ---- one-time setup -------------------------------------------------------
st.set_page_config(
    page_title="Kiirus Xpress — Logistics Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
seed_all_if_empty()
inject_global_css()  # respects st.session_state.theme_mode


# ---- nav definition -------------------------------------------------------
NAV_ITEMS: list[tuple[str, str, str, callable]] = [
    ("Landing",      "▣", "Overview",        landing.render),
    ("TAT Analysis", "◷", "Delivered SLA",   tat.render),
    ("Transit",      "⛟", "In flight",       transit.render),
    ("Customize",    "≡", "Ad-hoc query",    customize.render),
    ("Edit",         "✎", "Reference data",  edit.render),
]


LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"


def _logo_html(size: int = 40) -> str:
    """Return the brand icon as HTML: real logo if present, else a tinted box."""
    if LOGO_PATH.exists():
        try:
            b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
            return (
                f'<img src="data:image/png;base64,{b64}" '
                f'style="width:{size}px;height:{size}px;border-radius:10px;'
                f'object-fit:cover;background:{t("yellow_soft")};" />'
            )
        except Exception:
            pass
    return (
        f'<div style="width:{size}px;height:{size}px;'
        f'background:{t("yellow_soft")};border-radius:10px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:{t("yellow_primary")};font-size:{int(size * 0.55)}px;font-weight:700;">📦</div>'
    )


def _render_brand_block() -> None:
    st.sidebar.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:14px;padding:20px 16px 18px 16px;">
          {_logo_html(40)}
          <div>
            <div style="font-size:16px;font-weight:700;color:{t('text_primary')};letter-spacing:-0.01em;">
              Kiirus Xpress
            </div>
            <div style="font-size:10px;color:{t('text_muted')};text-transform:uppercase;
                        letter-spacing:0.12em;margin-top:2px;line-height:1.4;">
              LOGISTICS<br/>INTELLIGENCE
            </div>
          </div>
        </div>
        <div style="height:1px;background:{t('sidebar_border')};margin:0 16px;"></div>
        <div style="padding:18px 16px 8px 16px;font-size:11px;color:{t('sidebar_label')};
                    text-transform:uppercase;letter-spacing:0.12em;font-weight:600;">
          Workspace
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_active_nav_row(icon: str, label: str, sublabel: str) -> None:
    st.sidebar.markdown(
        f"""
        <div style="
          display:flex;align-items:center;gap:12px;
          padding:10px 12px;margin:2px 8px 4px 8px;
          background:{t('yellow_soft')};
          border:1px solid {t('yellow_edge')};
          border-radius:10px;
          min-height:56px;
        ">
          <div style="
            width:34px;height:34px;
            background:{t('yellow_soft')};
            border:1px solid {t('yellow_edge')};
            border-radius:8px;
            display:flex;align-items:center;justify-content:center;
            color:{t('yellow_primary')};font-size:18px;font-weight:600;
          ">{icon}</div>
          <div style="flex:1;">
            <div style="color:{t('yellow_primary')};font-size:14px;font-weight:600;line-height:1.2;">
              {label}
            </div>
            <div style="color:{t('text_muted')};font-size:11px;line-height:1.4;margin-top:2px;">
              {sublabel}
            </div>
          </div>
          <div style="width:7px;height:7px;border-radius:50%;background:{t('yellow_primary')};
                      box-shadow:{t('yellow_glow')};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_inactive_nav_row(icon: str, label: str, sublabel: str, key: str) -> bool:
    """Render as a single multi-line button. Returns True if clicked."""
    btn_label = f"{icon}    {label}\n        {sublabel}"
    return st.sidebar.button(
        btn_label,
        key=f"nav_btn_{key}",
        use_container_width=True,
    )


def _render_theme_toggle() -> None:
    st.sidebar.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    sb = t("sidebar_border")
    st.sidebar.markdown(
        f"<div style='height:1px;background:{sb};margin:8px 16px;'></div>",
        unsafe_allow_html=True,
    )
    current = st.session_state.get("theme_mode", "dark")
    new_val = st.sidebar.toggle(
        "🌗 Light mode",
        value=(current == "light"),
        key="theme_toggle",
    )
    new_mode = "light" if new_val else "dark"
    if new_mode != current:
        st.session_state["theme_mode"] = new_mode
        st.rerun()


def _render_footer() -> None:
    st.sidebar.markdown(
        f"""
        <div style="padding:14px 16px 18px 16px;">
          <div style="font-size:10px;color:{t('sidebar_label')};display:flex;align-items:center;gap:6px;">
            <span style="width:6px;height:6px;border-radius:50%;background:{t('footer_dot')};"></span>
            Local-only
          </div>
          <div style="font-size:10px;color:{t('sidebar_label')};display:flex;align-items:center;gap:6px;margin-top:4px;">
            <span style="width:6px;height:6px;border-radius:50%;background:{t('footer_dot')};"></span>
            Offline-ready
          </div>
          <div style="font-size:10px;color:{t('sidebar_label')};margin-top:8px;">
            Built for Kiirus Xpress
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> str:
    current = st.session_state.get("current_section", NAV_ITEMS[0][0])

    _render_brand_block()

    for label, icon, sublabel, _render in NAV_ITEMS:
        if label == current:
            _render_active_nav_row(icon, label, sublabel)
        else:
            clicked = _render_inactive_nav_row(icon, label, sublabel, key=label)
            if clicked:
                st.session_state["current_section"] = label
                st.rerun()

    _render_theme_toggle()
    _render_footer()

    return current


def main() -> None:
    current = _render_sidebar()
    for label, _icon, _sub, render_fn in NAV_ITEMS:
        if label == current:
            render_fn()
            return


SECTIONS = {label: render_fn for label, _i, _s, render_fn in NAV_ITEMS}


if __name__ == "__main__":
    main()
