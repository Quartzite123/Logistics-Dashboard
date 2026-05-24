"""Top-level ingest: read a Delhivery .xlsx file → append to shipments_raw →
dedup-merge into shipments_latest → store derived SLA columns.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd

from ..store.db import cursor
from ..store.schema import (
    RAW_COLUMNS, DERIVED_COLUMNS, DB_COL, DATE_COLUMNS, INT_COLUMNS, FLOAT_COLUMNS,
)
from .dedup import merge_into_latest, pick_winner
from .sla import compute_row
from .origin_lookup import clear_unknown_cities, get_unknown_cities


REQUIRED_COLUMNS = {"LRN", "Current Status", "Pickup Date", "Remarks"}


class IngestError(Exception):
    pass


def _normalise_value(col: str, v):
    """Coerce a single cell value into a sqlite-friendly type."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if col in DATE_COLUMNS:
        try:
            ts = pd.to_datetime(v, errors="coerce")
            if pd.isna(ts):
                return None
            return ts.isoformat()
        except Exception:
            return None
    if col in INT_COLUMNS:
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
    if col in FLOAT_COLUMNS:
        try:
            f = float(v)
            return None if pd.isna(f) else f
        except (ValueError, TypeError):
            return None
    return str(v)


def _read_workbook(file_like) -> pd.DataFrame:
    """Read an Excel file (path or BytesIO) into a DataFrame."""
    if isinstance(file_like, (str, Path)):
        df = pd.read_excel(file_like, sheet_name=0)
    else:
        # BytesIO / UploadedFile
        df = pd.read_excel(file_like, sheet_name=0, engine="openpyxl")
    return df


def validate_schema(df: pd.DataFrame) -> list[str]:
    """Return a list of WARNINGS (missing/extra columns). Raises IngestError if a
    REQUIRED column is missing."""
    cols = set(df.columns)
    missing_required = REQUIRED_COLUMNS - cols
    if missing_required:
        raise IngestError(
            f"Missing required columns: {sorted(missing_required)}"
        )
    missing_optional = set(RAW_COLUMNS) - cols
    extras = cols - set(RAW_COLUMNS)
    warnings: list[str] = []
    if missing_optional:
        warnings.append(
            f"{len(missing_optional)} optional column(s) missing — will be stored as NULL: "
            + ", ".join(sorted(missing_optional))[:200]
        )
    if extras:
        warnings.append(
            f"{len(extras)} unexpected column(s) in upload — will be ignored: "
            + ", ".join(sorted(extras))[:200]
        )
    return warnings


def _row_dict_from_pandas(record: dict) -> dict:
    """Build a {original_col: value} dict from a pandas record, filling missing cols."""
    out = {}
    for col in RAW_COLUMNS:
        if col in record:
            out[col] = record[col]
        else:
            out[col] = None
    return out


def ingest_file(file_like, filename: str) -> dict:
    """Ingest one Delhivery .xlsx. Returns a summary dict."""
    clear_unknown_cities()
    df = _read_workbook(file_like)
    warnings = validate_schema(df)

    batch_id = str(uuid.uuid4())
    uploaded_at = datetime.utcnow().isoformat()

    # Prepare rows.
    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        row = _row_dict_from_pandas(record)
        row["_upload_batch_id"] = batch_id
        row["_upload_filename"] = filename
        row["_uploaded_at"] = uploaded_at
        rows.append(row)

    # 1) Insert into shipments_raw (full audit archive).
    raw_id_by_index: dict[int, int] = _insert_raw(rows, batch_id, filename, uploaded_at)

    # 2) Pull existing latest by LRN, dedup-merge.
    incoming_lrns = {int(r["LRN"]) for r in rows if r.get("LRN") is not None}
    existing_by_lrn = _fetch_latest_by_lrn(incoming_lrns)
    to_insert, to_update, skipped = merge_into_latest(rows, existing_by_lrn)

    # 3) Compute derived SLA columns for every winner, write to shipments_latest.
    n_inserted = _upsert_latest(to_insert + to_update, raw_id_by_index)

    # 4) Record upload history.
    rows_new = len(to_insert)
    rows_updated = len(to_update)
    rows_skipped = len(skipped)
    _record_upload(batch_id, filename, uploaded_at, len(rows), rows_new, rows_updated, rows_skipped)

    return {
        "batch_id": batch_id,
        "filename": filename,
        "rows_in": len(rows),
        "rows_new": rows_new,
        "rows_updated": rows_updated,
        "rows_skipped": rows_skipped,
        "warnings": warnings,
        "unknown_origin_cities": get_unknown_cities(),
    }


def _insert_raw(rows: list[dict], batch_id: str, filename: str, uploaded_at: str) -> dict[int, int]:
    """Insert all rows into shipments_raw. Returns {row_index: raw_id} mapping."""
    cols_sql = ", ".join(f'"{DB_COL[c]}"' for c in RAW_COLUMNS)
    placeholders = ", ".join("?" for _ in RAW_COLUMNS)
    sql = (
        "INSERT INTO shipments_raw "
        f"(_upload_batch_id, _upload_filename, _uploaded_at, {cols_sql}) "
        f"VALUES (?, ?, ?, {placeholders})"
    )
    idx_to_raw_id: dict[int, int] = {}
    with cursor() as cur:
        for i, r in enumerate(rows):
            values = [batch_id, filename, uploaded_at] + [
                _normalise_value(c, r.get(c)) for c in RAW_COLUMNS
            ]
            cur.execute(sql, values)
            idx_to_raw_id[i] = cur.lastrowid
    return idx_to_raw_id


def _fetch_latest_by_lrn(lrns: Iterable[int]) -> dict[int, dict]:
    """Return {lrn: existing_row_dict_with_display_col_names} for the given LRNs."""
    lrns = list(lrns)
    if not lrns:
        return {}
    placeholders = ",".join("?" for _ in lrns)
    cols_sql = ", ".join(f'"{DB_COL[c]}" AS "{c}"' for c in RAW_COLUMNS)
    sql = f"SELECT {cols_sql} FROM shipments_latest WHERE lrn IN ({placeholders})"
    out: dict[int, dict] = {}
    with cursor() as cur:
        cur.execute(sql, lrns)
        for row in cur.fetchall():
            d = dict(row)
            out[int(d["LRN"])] = d
    return out


def _upsert_latest(winners: list[dict], raw_id_by_index: dict[int, int]) -> int:
    """Insert / replace winners in shipments_latest with derived SLA columns."""
    if not winners:
        return 0

    # Pre-compute derived columns OUTSIDE the outer cursor — origin_lookup writes
    # to origin_recents, and nesting two connections deadlocks SQLite under WAL.
    derived_by_idx = [compute_row(w) for w in winners]

    raw_cols_db = [DB_COL[c] for c in RAW_COLUMNS]
    all_cols = raw_cols_db + DERIVED_COLUMNS + ["_source_raw_id", "_updated_at"]
    cols_sql = ", ".join(f'"{c}"' for c in all_cols)
    placeholders = ", ".join("?" for _ in all_cols)
    sql = (
        "INSERT INTO shipments_latest "
        f"({cols_sql}) VALUES ({placeholders}) "
        "ON CONFLICT(lrn) DO UPDATE SET "
        + ", ".join(f'"{c}" = excluded."{c}"' for c in all_cols if c != "lrn")
    )
    now = datetime.utcnow().isoformat()
    with cursor() as cur:
        for i, w in enumerate(winners):
            derived = derived_by_idx[i]
            raw_values = [_normalise_value(c, w.get(c)) for c in RAW_COLUMNS]
            derived_values = [derived[c] for c in DERIVED_COLUMNS]
            # _source_raw_id isn't strictly necessary; we leave NULL for updates.
            values = raw_values + derived_values + [None, now]
            cur.execute(sql, values)
    return len(winners)


def _record_upload(batch_id, filename, uploaded_at, rows_in, rows_new, rows_updated, rows_skipped):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO uploads(batch_id, filename, uploaded_at, rows_in, rows_new, rows_updated, rows_skipped) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (batch_id, filename, uploaded_at, rows_in, rows_new, rows_updated, rows_skipped),
        )


def recompute_all_sla() -> int:
    """Recompute and store derived SLA columns for every row in shipments_latest.

    Used after a first-time pincode-master load (when historical rows are still
    N/A). After that, the §19 forward-only rule kicks in and matrix/ODA edits do
    NOT call this function.
    """
    cols_sql = ", ".join(f'"{DB_COL[c]}" AS "{c}"' for c in RAW_COLUMNS)
    with cursor() as cur:
        cur.execute(f"SELECT lrn, {cols_sql} FROM shipments_latest")
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return 0

    # Pre-compute derived columns OUTSIDE the outer cursor — origin_lookup writes
    # to origin_recents, and nesting two connections deadlocks SQLite under WAL.
    derived_by_idx = [compute_row(r) for r in rows]

    update_sql = (
        "UPDATE shipments_latest SET "
        + ", ".join(f'"{c}" = ?' for c in DERIVED_COLUMNS)
        + ", _updated_at = ? WHERE lrn = ?"
    )
    now = datetime.utcnow().isoformat()
    with cursor() as cur:
        for i, r in enumerate(rows):
            derived = derived_by_idx[i]
            values = [derived[c] for c in DERIVED_COLUMNS] + [now, r["LRN"]]
            cur.execute(update_sql, values)
    return len(rows)
