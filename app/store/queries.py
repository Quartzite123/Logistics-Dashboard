"""High-level query helpers — return pandas DataFrames with display column names."""
from __future__ import annotations

import pandas as pd

from .db import cursor
from .schema import RAW_COLUMNS, DERIVED_COLUMNS, DB_COL


def get_monthly_trend() -> pd.DataFrame:
    """Month-on-month order volume + SLA bucket counts, keyed by Manifest Date."""
    with cursor() as c:
        c.execute(
            """
            SELECT
                strftime('%Y-%m', manifest_date) AS month,
                COUNT(*) AS total_orders,
                SUM(CASE WHEN _sla_status='Early'   THEN 1 ELSE 0 END) AS early,
                SUM(CASE WHEN _sla_status='On Time' THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN _sla_status='Late'    THEN 1 ELSE 0 END) AS late
            FROM shipments_latest
            WHERE manifest_date IS NOT NULL
            GROUP BY month
            ORDER BY month
            """
        )
        rows = [tuple(r) for r in c.fetchall()]
    return pd.DataFrame(
        rows, columns=["month", "total_orders", "early", "on_time", "late"]
    )


def load_latest() -> pd.DataFrame:
    """Return shipments_latest as a DataFrame with display column names."""
    select_pieces = [f'"{DB_COL[c]}" AS "{c}"' for c in RAW_COLUMNS]
    select_pieces += [f'"{c}" AS "{c}"' for c in DERIVED_COLUMNS]
    sql = f'SELECT {", ".join(select_pieces)} FROM shipments_latest'
    with cursor() as cur:
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
    df = pd.DataFrame(rows)
    if df.empty:
        # Return an empty frame with the full expected columns
        return pd.DataFrame(columns=RAW_COLUMNS + DERIVED_COLUMNS)
    # Coerce known date columns into datetime for downstream pandas ops
    from .schema import DATE_COLUMNS
    for c in DATE_COLUMNS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def load_raw_for_lrn(lrn: int) -> pd.DataFrame:
    """Return all shipments_raw rows for a single LRN (audit drill-down)."""
    select_pieces = (
        ["id AS _id", "_upload_batch_id", "_upload_filename", "_uploaded_at"]
        + [f'"{DB_COL[c]}" AS "{c}"' for c in RAW_COLUMNS]
    )
    sql = f'SELECT {", ".join(select_pieces)} FROM shipments_raw WHERE lrn = ?'
    with cursor() as cur:
        cur.execute(sql, (lrn,))
        rows = [dict(r) for r in cur.fetchall()]
    return pd.DataFrame(rows)


def load_uploads_history() -> pd.DataFrame:
    with cursor() as cur:
        cur.execute(
            "SELECT batch_id, filename, uploaded_at, rows_in, rows_new, "
            "rows_updated, rows_skipped FROM uploads ORDER BY uploaded_at DESC"
        )
        rows = [dict(r) for r in cur.fetchall()]
    return pd.DataFrame(rows)


def count_latest() -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM shipments_latest")
        return cur.fetchone()[0]


def count_pincodes() -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pincode_master_live")
        return cur.fetchone()[0]
