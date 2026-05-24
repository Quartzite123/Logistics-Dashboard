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

import streamlit as st

from ..components import kpi_cards, chart_pair
from ..components.theme import render_section_header
from ..components.upload_dialog import open_upload_dialog
from ..store.queries import load_latest


def render() -> None:
    upload_clicked = render_section_header("Landing", show_upload_button=True)
    if upload_clicked:
        open_upload_dialog()

    df = load_latest()
    kpi_cards.render(df)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Vertically stacked chart pair: top pie + bottom selectable.
    top = st.container()
    bottom = st.container()
    chart_pair.render(df, section_key="landing", top_box=top, bottom_box=bottom)
