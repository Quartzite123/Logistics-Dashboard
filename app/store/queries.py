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


def get_aggregate_by_company() -> pd.DataFrame:
    """Per-company totals, order share, and status / SLA bucket counts."""
    with cursor() as c:
        c.execute(
            """
            SELECT
                s.order_id                                    AS company,
                COUNT(*)                                      AS total_orders,
                ROUND(COUNT(*)*100.0 / SUM(COUNT(*)) OVER(),1) AS order_share_pct,
                SUM(CASE WHEN s.current_status='Delivered' THEN 1 ELSE 0 END) AS delivered,
                SUM(CASE WHEN s.current_status NOT IN ('Delivered','RTO') THEN 1 ELSE 0 END) AS in_transit,
                SUM(CASE WHEN s._sla_status='Early'   THEN 1 ELSE 0 END) AS early,
                SUM(CASE WHEN s._sla_status='On Time' THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN s._sla_status='Late'    THEN 1 ELSE 0 END) AS late,
                SUM(CASE WHEN s.current_status='RTO'  THEN 1 ELSE 0 END) AS rto
            FROM shipments_latest s
            GROUP BY s.order_id
            ORDER BY total_orders DESC
            """
        )
        rows = [tuple(r) for r in c.fetchall()]
    return pd.DataFrame(
        rows,
        columns=[
            "company", "total_orders", "order_share_pct", "delivered",
            "in_transit", "early", "on_time", "late", "rto",
        ],
    )


def get_monthly_by_company() -> pd.DataFrame:
    """Per-company, per-month order volume + SLA buckets, keyed on Manifest Date."""
    with cursor() as c:
        c.execute(
            """
            SELECT
                s.order_id AS company,
                strftime('%Y-%m', s.manifest_date) AS month,
                COUNT(*) AS total,
                SUM(CASE WHEN s._sla_status='Early'   THEN 1 ELSE 0 END) AS early,
                SUM(CASE WHEN s._sla_status='On Time' THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN s._sla_status='Late'    THEN 1 ELSE 0 END) AS late,
                SUM(CASE WHEN s.current_status NOT IN ('Delivered','RTO') THEN 1 ELSE 0 END) AS not_delivered
            FROM shipments_latest s
            WHERE s.manifest_date IS NOT NULL
            GROUP BY s.order_id, month
            ORDER BY s.order_id, month
            """
        )
        rows = [tuple(r) for r in c.fetchall()]
    return pd.DataFrame(
        rows,
        columns=[
            "company", "month", "total", "early", "on_time", "late", "not_delivered",
        ],
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
