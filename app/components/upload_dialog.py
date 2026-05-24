"""Upload dialog — invoked from each section's header.

Replaces the inline upload panel that used to sit on the Landing page
(README §12 spec revision per CLAUDE_CODE_UI_PROMPT.md).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..pipeline.ingest import ingest_file, IngestError


@st.dialog("Upload new file(s)", width="large")
def open_upload_dialog() -> None:
    """Modal dialog: pick files → preview → process → close + refresh."""
    st.caption("Drag in one or more Delhivery .xlsx exports. We deduplicate by LRN.")

    files = st.file_uploader(
        "Files",
        type=["xlsx"],
        accept_multiple_files=True,
        key="dialog_uploader",
        label_visibility="collapsed",
    )

    if files:
        with st.expander(f"Preview {len(files)} file(s)", expanded=True):
            for f in files:
                try:
                    preview = pd.read_excel(f, sheet_name=0, nrows=5)
                    st.markdown(f"**{f.name}**")
                    st.dataframe(preview, hide_index=True, height=180)
                    f.seek(0)
                except Exception as e:
                    st.error(f"Cannot preview **{f.name}**: {e}")

    cols = st.columns([1, 1])
    with cols[0]:
        process = st.button(
            "Process & Update",
            type="primary",
            use_container_width=True,
            disabled=not files,
            key="dialog_process",
        )
    with cols[1]:
        cancel = st.button(
            "Cancel",
            use_container_width=True,
            key="dialog_cancel",
        )

    if cancel:
        st.rerun()
        return

    if process and files:
        results = []
        with st.spinner("Processing…"):
            for f in files:
                try:
                    f.seek(0)
                    summary = ingest_file(f, filename=f.name)
                    results.append((f.name, summary, None))
                except IngestError as e:
                    results.append((f.name, None, f"Schema error: {e}"))
                except Exception as e:
                    results.append((f.name, None, f"Unexpected: {e}"))

        for name, summary, err in results:
            if err is not None:
                st.error(f"**{name}** — {err}")
                continue
            st.success(
                f"**{name}** — {summary['rows_in']} rows · "
                f"{summary['rows_new']} new · {summary['rows_updated']} updated · "
                f"{summary['rows_skipped']} skipped"
            )
            unknown = summary.get("unknown_origin_cities", set())
            if unknown:
                city_list = ", ".join(f'"{c}"' for c in sorted(unknown))
                st.warning(
                    f"⚠️ **Unknown origin city detected**: {city_list}. "
                    f"Zone could not be resolved for these shipments — SLA will show N/A. "
                    f"If this is a new pickup city, ask your developer to add it to "
                    f"`app/data/origin_city_master.csv`."
                )
            for w in summary["warnings"]:
                st.warning(w)

        # If everything succeeded, auto-close & refresh.
        if all(r[2] is None for r in results):
            st.session_state["_upload_complete_refresh"] = True
            st.rerun()
