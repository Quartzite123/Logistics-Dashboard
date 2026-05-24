"""Layout helpers — preset ratio split between table (left) and chart pair (right)."""
from __future__ import annotations

from typing import Literal

import streamlit as st


HorizontalPreset = Literal["60/40", "50/50", "70/30", "Table only", "Charts only"]
VerticalPreset = Literal["50/50", "70/30", "30/70", "Pie only", "Selectable only"]

H_PRESETS: dict[str, tuple[int, int]] = {
    "60/40": (60, 40),
    "50/50": (50, 50),
    "70/30": (70, 30),
    "Table only": (100, 0),
    "Charts only": (0, 100),
}

V_PRESETS: dict[str, tuple[int, int]] = {
    "50/50": (50, 50),
    "70/30": (70, 30),
    "30/70": (30, 70),
    "Pie only": (100, 0),
    "Selectable only": (0, 100),
}


def horizontal_split(section_key: str, default: HorizontalPreset = "60/40"):
    """Render the preset-ratio toolbar and return (left_col, right_col).

    Either col may be `None` when the preset is `Table only` / `Charts only`.
    `section_key` namespaces session-state so different tabs remember their own choice.
    """
    state_key = f"_h_preset_{section_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = default

    chosen = st.segmented_control(
        "Layout",
        options=list(H_PRESETS.keys()),
        default=st.session_state[state_key],
        key=f"h_seg_{section_key}",
        label_visibility="collapsed",
    )
    if chosen is None:
        chosen = st.session_state[state_key]
    st.session_state[state_key] = chosen

    left_pct, right_pct = H_PRESETS[chosen]
    if left_pct == 0:
        return None, st.container()
    if right_pct == 0:
        return st.container(), None
    left_col, right_col = st.columns([left_pct, right_pct], gap="medium")
    return left_col, right_col


def vertical_split(section_key: str, container, default: VerticalPreset = "50/50"):
    """Render a vertical-split toolbar inside `container` and return (top_box, bottom_box).

    Streamlit can't truly stack-and-size containers, so we just return two child
    containers and rely on caller layout. Either may be `None` based on preset.
    """
    with container:
        state_key = f"_v_preset_{section_key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = default

        chosen = st.segmented_control(
            "Vertical layout",
            options=list(V_PRESETS.keys()),
            default=st.session_state[state_key],
            key=f"v_seg_{section_key}",
            label_visibility="collapsed",
        )
        if chosen is None:
            chosen = st.session_state[state_key]
        st.session_state[state_key] = chosen

        top_pct, bot_pct = V_PRESETS[chosen]
        if top_pct == 0:
            return None, st.container()
        if bot_pct == 0:
            return st.container(), None
        return st.container(), st.container()
