"""Section 5 — Edit (README §16). Two sub-tabs: Region Matrix, Pincode Master.

Restyled per CLAUDE_CODE_UI_PROMPT.md:
- Section title with accent (NO upload trigger button — Edit doesn't show upload).
- Matrix editor: 5×5 grid with subtle yellow-soft tint on diagonal cells.
- Draft banner when staged edits exist.
- Pincode editor paginated (25 rows/page) over search-matched subset.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..components.modals import confirm_button
from ..components.theme import render_section_header, YELLOW_SOFT
from ..store.db import cursor
from ..store.schema import ZONES
from ..store.seed import get_live_matrix, STATE_ZONE
from ..store.queries import count_pincodes
from ..pipeline.zones import clear_caches as zones_clear_caches
from ..pipeline.ingest import recompute_all_sla


PAGE_SIZE = 25


def _normalise_oda(raw_value) -> str:
    """Maps source file ODA text to canonical 'YES' / 'NO'."""
    if raw_value is None:
        return "NO"
    v = str(raw_value).strip().lower()
    if v in ("oda", "yes", "y", "1", "true"):
        return "YES"
    if v in ("normal service", "no", "n", "0", "false", ""):
        return "NO"
    return "NO"   # safe default


def render() -> None:
    # Edit has NO upload button — that workflow lives on the other 4 sections.
    render_section_header("Edit", show_upload_button=False)

    tab1, tab2 = st.tabs(["Region Matrix", "Pincode Master"])
    with tab1:
        _render_matrix_tab()
    with tab2:
        _render_pincode_tab()


# ---------------------------------------------------------------------------
# Region Matrix sub-tab
# ---------------------------------------------------------------------------

def _render_matrix_tab() -> None:
    st.markdown("### 5×5 Region SLA matrix")
    st.caption(
        "Diagonal = intra-zone TAT (yellow-tinted). Values are days. "
        "Edits affect future uploads only — past shipments keep their "
        "already-stored Expected TAT."
    )

    live = _matrix_to_frame(get_live_matrix())

    draft_exists = _draft_matrix_exists()
    if draft_exists:
        st.markdown(
            '<div class="draft-banner">⚠ Draft changes pending — '
            'Apply to make them live or Discard to revert.</div>',
            unsafe_allow_html=True,
        )

    is_editing = st.session_state.get("_matrix_editing", False)

    if not is_editing and not draft_exists:
        _render_matrix_readonly(live)
        if confirm_button(
            "Edit matrix",
            "Changes cannot be reverted once applied. Continue?",
            section_key="matrix_enter_edit",
            on_confirm=lambda: st.session_state.update({"_matrix_editing": True}),
        ):
            st.rerun()
        return

    if is_editing:
        st.markdown("**Editing — change cells, then Save**")
        edited = st.data_editor(
            live,
            use_container_width=True,
            num_rows="fixed",
            key="matrix_editor",
        )
        c1, c2 = st.columns(2)
        if c1.button("Save (stage draft)", type="primary", key="matrix_save"):
            try:
                _validate_matrix(edited)
                _save_matrix_draft(edited)
                st.session_state["_matrix_editing"] = False
                st.success("Draft saved. Click Apply below to make changes live.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if c2.button("Discard", key="matrix_discard"):
            st.session_state["_matrix_editing"] = False
            st.rerun()
        return

    # Draft exists → show + Apply / Discard
    draft = _matrix_draft_to_frame()
    st.markdown("**Draft (pending Apply)**")
    _render_matrix_readonly(draft)

    c1, c2 = st.columns(2)
    with c1:
        if confirm_button(
            "Apply draft → live",
            "This will change SLA calculations for FUTURE uploads. Past shipments are not affected. Cannot be reverted.",
            section_key="matrix_apply",
            on_confirm=_apply_matrix_draft,
        ):
            st.success("Live matrix updated.")
            st.rerun()
    if c2.button("Discard draft", key="matrix_discard_draft"):
        _discard_matrix_draft()
        st.rerun()


def _render_matrix_readonly(df: pd.DataFrame) -> None:
    """Render the matrix with yellow-soft diagonal cells."""
    def _style(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for o in data.index:
            for d in data.columns:
                if o == d and o in ZONES and d in ZONES:
                    styles.at[o, d] = (
                        f"background-color: {YELLOW_SOFT};"
                        " color: #FFD60A; font-weight: 600;"
                        " font-family: 'JetBrains Mono', monospace;"
                    )
                else:
                    styles.at[o, d] = (
                        " font-family: 'JetBrains Mono', monospace;"
                    )
        return styles

    st.dataframe(df.style.apply(_style, axis=None), use_container_width=True)


def _matrix_to_frame(m: dict[tuple[str, str], int]) -> pd.DataFrame:
    rows = []
    for o in ZONES:
        rows.append({d: m.get((o, d), 0) for d in ZONES})
    return pd.DataFrame(rows, index=ZONES)


def _validate_matrix(df: pd.DataFrame) -> None:
    for o in ZONES:
        for d in ZONES:
            v = df.at[o, d]
            if pd.isna(v) or int(v) < 0:
                raise ValueError(f"Cell ({o} → {d}) must be a non-negative integer")


def _save_matrix_draft(df: pd.DataFrame) -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM sla_matrix_draft")
        rows = [(o, d, int(df.at[o, d])) for o in ZONES for d in ZONES]
        cur.executemany(
            "INSERT INTO sla_matrix_draft(origin_zone, destination_zone, days) VALUES (?, ?, ?)",
            rows,
        )


def _draft_matrix_exists() -> bool:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sla_matrix_draft")
        return cur.fetchone()[0] > 0


def _matrix_draft_to_frame() -> pd.DataFrame:
    with cursor() as cur:
        cur.execute("SELECT origin_zone, destination_zone, days FROM sla_matrix_draft")
        m = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    return _matrix_to_frame(m)


def _apply_matrix_draft() -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM sla_matrix_live")
        cur.execute(
            "INSERT INTO sla_matrix_live(origin_zone, destination_zone, days) "
            "SELECT origin_zone, destination_zone, days FROM sla_matrix_draft"
        )
        cur.execute("DELETE FROM sla_matrix_draft")


def _discard_matrix_draft() -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM sla_matrix_draft")


# ---------------------------------------------------------------------------
# Pincode Master sub-tab — paginated search-and-edit + bulk re-upload
# ---------------------------------------------------------------------------

def _render_pincode_tab() -> None:
    st.markdown("### 22 K pincode master")
    n = count_pincodes()
    st.caption(f"Currently {n:,} pincodes in the live master.")

    if n == 0:
        st.warning(
            "No pincode master loaded yet. Region / ODA / Expected TAT will "
            "remain N/A across the dashboard until you upload one."
        )

    if _pincode_draft_count() > 0:
        st.markdown(
            '<div class="draft-banner">⚠ Draft changes pending — '
            f'{_pincode_draft_count():,} pincode rows ready to Apply.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### A. Search and edit individual pincodes")
    _search_and_edit()

    st.divider()

    st.markdown("#### B. Bulk re-upload (replace entire master)")
    _bulk_upload()


def _search_and_edit() -> None:
    query = st.text_input(
        "Search by pincode or city name",
        key="pincode_search",
        placeholder="e.g. 411001 or Aurangabad",
    )
    if not query:
        st.caption("Type to search.")
        return

    rows = _search_pincodes(query.strip())
    if not rows:
        st.info("No matches.")
        return

    df = pd.DataFrame(rows)

    # Pagination over the matching subset.
    n = len(df)
    page = st.session_state.get(f"_pincode_page_{query}", 0)
    page_count = max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, page_count - 1))
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, n)
    df_page = df.iloc[start:end].reset_index(drop=True)

    st.caption(f"Showing {start + 1}–{end} of {n} matching rows.")
    edited = st.data_editor(
        df_page,
        use_container_width=True,
        num_rows="dynamic",
        key=f"pincode_editor_{query}_{page}",
        column_config={
            "zone": st.column_config.SelectboxColumn(options=ZONES, required=True),
            "oda":  st.column_config.SelectboxColumn(options=["YES", "NO"], required=True),
        },
    )

    nav_cols = st.columns([1, 2, 1])
    if nav_cols[0].button("← Previous", disabled=(page == 0), key=f"prev_{query}"):
        st.session_state[f"_pincode_page_{query}"] = page - 1
        st.rerun()
    nav_cols[1].markdown(
        f"<div style='text-align: center; color: var(--text-muted); padding-top: 8px;'>"
        f"Page {page + 1} of {page_count}</div>",
        unsafe_allow_html=True,
    )
    if nav_cols[2].button("Next →", disabled=(page >= page_count - 1), key=f"next_{query}"):
        st.session_state[f"_pincode_page_{query}"] = page + 1
        st.rerun()

    if st.button("Save changes (stage draft)", type="primary", key="pincode_save"):
        try:
            _validate_pincodes(edited)
            _save_pincode_changes(edited)
            st.success("Draft saved. Click Apply below to make live.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if _pincode_draft_count() > 0:
        if confirm_button(
            "Apply pincode draft → live",
            "This replaces the live pincode master. Future uploads will use the new master.",
            section_key="pincode_apply",
            on_confirm=_apply_pincode_draft,
        ):
            st.rerun()


def _search_pincodes(q: str, limit: int = 1000) -> list[dict]:
    """Search by pincode prefix or city substring."""
    with cursor() as cur:
        if q.isdigit():
            cur.execute(
                "SELECT pincode, city, state, zone, oda FROM pincode_master_live "
                "WHERE pincode LIKE ? LIMIT ?",
                (q + "%", limit),
            )
        else:
            cur.execute(
                "SELECT pincode, city, state, zone, oda FROM pincode_master_live "
                "WHERE LOWER(city) LIKE ? LIMIT ?",
                ("%" + q.lower() + "%", limit),
            )
        return [dict(r) for r in cur.fetchall()]


def _validate_pincodes(df: pd.DataFrame) -> None:
    seen = set()
    for _, row in df.iterrows():
        p = str(row.get("pincode") or "").strip()
        if not p.isdigit() or len(p) != 6:
            raise ValueError(f"Pincode {p!r} must be 6 digits")
        if p in seen:
            raise ValueError(f"Duplicate pincode {p!r}")
        seen.add(p)
        if row.get("zone") not in ZONES:
            raise ValueError(f"Pincode {p}: zone must be one of {ZONES}")
        if str(row.get("oda")).upper() not in ("YES", "NO"):
            raise ValueError(f"Pincode {p}: ODA must be YES or NO")


def _save_pincode_changes(df: pd.DataFrame) -> None:
    with cursor() as cur:
        for _, r in df.iterrows():
            p = str(r["pincode"]).strip()
            cur.execute(
                "INSERT INTO pincode_master_draft(pincode, city, state, zone, oda) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(pincode) DO UPDATE SET "
                "city=excluded.city, state=excluded.state, "
                "zone=excluded.zone, oda=excluded.oda",
                (p, r.get("city"), r.get("state"), r["zone"], _normalise_oda(r.get("oda"))),
            )


def _pincode_draft_count() -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pincode_master_draft")
        return cur.fetchone()[0]


def _apply_pincode_draft() -> None:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO pincode_master_live(pincode, city, state, zone, oda) "
            "SELECT pincode, city, state, zone, oda FROM pincode_master_draft "
            "WHERE TRUE "
            "ON CONFLICT(pincode) DO UPDATE SET "
            "city=excluded.city, state=excluded.state, "
            "zone=excluded.zone, oda=excluded.oda"
        )
        cur.execute("DELETE FROM pincode_master_draft")
    zones_clear_caches()


def _bulk_upload() -> None:
    # Surface any warnings stashed by the previous Apply (e.g. unknown states).
    _last_warn = st.session_state.pop("_pincode_bulk_warnings", None)
    if _last_warn:
        st.warning(_last_warn)

    file = st.file_uploader(
        "Replace entire pincode master with an .xlsx",
        type=["xlsx"],
        key="pincode_bulk_uploader",
        help="Required: 'Pin', 'State Name'. Optional: 'ODA' (defaults to NO). 'Sr No' is ignored. Zone is derived from State Name.",
    )
    if file is None:
        return
    try:
        df = pd.read_excel(file, sheet_name=0)
        cols_ci = {str(c).lower().strip(): c for c in df.columns}
        if "pin" not in cols_ci or "state name" not in cols_ci:
            st.error("File must contain columns: 'Pin' and 'State Name' (ODA optional).")
            return
        rename_map = {cols_ci["pin"]: "Pin", cols_ci["state name"]: "State Name"}
        if "oda" in cols_ci:
            rename_map[cols_ci["oda"]] = "ODA"
        df = df.rename(columns=rename_map)
        st.markdown(f"**Preview** — {len(df):,} rows")
        st.dataframe(df.head(20), use_container_width=True)
        if confirm_button(
            "Replace live master with this file",
            f"This will REPLACE all {count_pincodes():,} existing pincode rows with {len(df):,} new rows. "
            "First-time load: SLA will be recomputed for existing shipments.",
            section_key="pincode_bulk_apply",
            on_confirm=lambda: _replace_live_pincodes(df),
        ):
            st.rerun()
    except Exception as e:
        st.error(f"Failed to read file: {e}")


def _replace_live_pincodes(df: pd.DataFrame) -> None:
    n_before = count_pincodes()
    rows: list[tuple] = []
    unknown_states: set[str] = set()
    skipped_bad_pin = 0

    for _, r in df.iterrows():
        # Pin → pincode (string, 6 digits). Handle int/float/string from Excel.
        raw_pin = r.get("Pin")
        if pd.isna(raw_pin):
            skipped_bad_pin += 1
            continue
        try:
            p = str(int(float(raw_pin)))
        except (ValueError, TypeError):
            p = str(raw_pin).strip()
        if not p.isdigit() or len(p) != 6:
            skipped_bad_pin += 1
            continue

        # State Name → zone via STATE_ZONE (already {state: zone}).
        state_raw = r.get("State Name")
        state = "" if pd.isna(state_raw) else str(state_raw).strip()
        zone = STATE_ZONE.get(state)
        if zone is None:
            if state:
                unknown_states.add(state)
            continue

        # ODA optional; defaults to NO if missing.
        oda = _normalise_oda(r.get("ODA"))

        rows.append((p, None, state, zone, oda))   # city = None (not in source)

    with cursor() as cur:
        cur.execute("DELETE FROM pincode_master_live")
        cur.executemany(
            "INSERT INTO pincode_master_live(pincode, city, state, zone, oda) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    zones_clear_caches()
    if n_before == 0:
        recompute_all_sla()

    msgs: list[str] = []
    if unknown_states:
        sample = ", ".join(sorted(unknown_states)[:8])
        more = "" if len(unknown_states) <= 8 else f" (+{len(unknown_states) - 8} more)"
        msgs.append(f"Skipped rows for {len(unknown_states)} unknown state name(s): {sample}{more}")
    if skipped_bad_pin:
        msgs.append(f"Skipped {skipped_bad_pin} row(s) with invalid/blank pincode.")
    if msgs:
        st.session_state["_pincode_bulk_warnings"] = " · ".join(msgs)
