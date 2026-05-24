"""Confirm-dialog helpers used by Section 5 — Edit (Save→Apply with warnings)."""
from __future__ import annotations

from typing import Callable, Optional

import streamlit as st


def confirm_button(
    label: str,
    warning: str,
    section_key: str,
    on_confirm: Optional[Callable[[], None]] = None,
    button_type: str = "primary",
) -> bool:
    """A two-step confirm-button pattern.

    First click stores `armed_<section_key>=True` in session_state and shows
    `warning`. Second click (which appears as 'Confirm' on the same button)
    invokes `on_confirm`. Returns True the second time, False otherwise.

    Designed for inline warnings without a true modal (Streamlit's dialog
    API is still limited and doesn't behave well under stlite).
    """
    armed_key = f"_armed_{section_key}"
    armed = st.session_state.get(armed_key, False)

    if not armed:
        if st.button(label, key=f"btn_{section_key}", type=button_type):
            st.session_state[armed_key] = True
            st.rerun()
        return False

    st.warning(warning)
    c1, c2 = st.columns([1, 1])
    if c1.button(f"✓ Confirm {label}", key=f"btn_confirm_{section_key}", type="primary"):
        st.session_state[armed_key] = False
        if on_confirm is not None:
            on_confirm()
        return True
    if c2.button("Cancel", key=f"btn_cancel_{section_key}"):
        st.session_state[armed_key] = False
        st.rerun()
    return False
