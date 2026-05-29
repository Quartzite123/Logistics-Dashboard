"""Minimal page-level injection: fonts + html data-attrs + sidebar flatten.

The heavy CSS lives inside the custom-component iframes — see
`_html/sidebar/styles.css` and `_html/kpi_grid/styles.css`. This module
exists only to:

 1. Load Inter + JetBrains Mono in the outer document.
 2. Mirror `st.session_state` (theme_mode / density / sidebar_width) onto
    `<html data-theme="..." data-density="..." data-sidebar="...">` so any
    native Streamlit element can react to theme via CSS attribute selectors.
 3. Flatten Streamlit's default sidebar wrapper so the iframe sits flush.
"""
from __future__ import annotations

import streamlit as st


def inject_global_styles() -> None:
    """Run on every rerun. Idempotent."""
    theme = st.session_state.get("theme_mode", "dark")
    density = st.session_state.get("density", "balanced")
    sidebar_width = st.session_state.get("sidebar_width", "standard")

    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
          html {{ font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; }}
          section[data-testid="stSidebar"] > div:first-child {{
            padding: 0 !important;
            background: transparent !important;
          }}
          section[data-testid="stSidebar"] .stIFrame iframe {{ display: block; border: 0; }}

          [data-testid="stDataFrameToolbarButton"]:has([aria-label="Download as CSV"]) {{ display: none !important; }}
          button[title="Download as CSV"] {{ display: none !important; }}

          [data-testid="stPlotlyChart"] {{
            touch-action: pan-x pan-y pinch-zoom !important;
          }}
          [data-testid="stPlotlyChart"] * {{
            touch-action: inherit !important;
          }}
          .js-plotly-plot,
          .js-plotly-plot * {{
            touch-action: pan-x pan-y pinch-zoom !important;
          }}
        </style>
        <script>
          (function () {{
            try {{
              const root = window.parent.document.documentElement;
              root.dataset.theme = "{theme}";
              root.dataset.density = "{density}";
              root.dataset.sidebar = "{sidebar_width}";
              document.documentElement.dataset.theme = "{theme}";
              document.documentElement.dataset.density = "{density}";
              document.documentElement.dataset.sidebar = "{sidebar_width}";
            }} catch (e) {{}}
          }})();
        </script>
        """,
        unsafe_allow_html=True,
    )
