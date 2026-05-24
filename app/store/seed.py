"""Seed the database with bundled reference data (matrix + state→zone fallback).

Run on first launch, or whenever the live matrix table is empty.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .db import cursor
from .schema import ZONES

MATRIX_CSV = Path(__file__).resolve().parent.parent / "reference" / "matrix.csv"


# Hardcoded Indian state → zone mapping (used when pincode lookup misses).
# Covers all 28 states + UTs. Editable here only — not via the dashboard.
STATE_ZONE: dict[str, str] = {
    # West
    "Maharashtra": "West", "Gujarat": "West", "Goa": "West",
    "Rajasthan": "West", "Madhya Pradesh": "West",
    "Daman and Diu": "West", "Daman & Diu": "West",
    "Dadra and Nagar Haveli": "West",

    # South
    "Karnataka": "South", "Tamil Nadu": "South", "Kerala": "South",
    "Andhra Pradesh": "South", "Telangana": "South",
    "Puducherry": "South", "Pondicherry": "South",
    "Lakshadweep": "South",

    # North
    "Delhi": "North", "Haryana": "North", "Punjab": "North",
    "Uttar Pradesh": "North", "Uttarakhand": "North",
    "Himachal Pradesh": "North", "Jammu & Kashmir": "North",
    "Jammu and Kashmir": "North", "Ladakh": "North",
    "Chandigarh": "North",

    # East
    "West Bengal": "East", "Bihar": "East", "Jharkhand": "East",
    "Odisha": "East", "Orissa": "East", "Chhattisgarh": "East",
    "Sikkim": "East",
    "Andaman and Nicobar Islands": "East",

    # North-East
    "Assam": "North-East", "Arunachal Pradesh": "North-East",
    "Meghalaya": "North-East", "Manipur": "North-East",
    "Mizoram": "North-East", "Nagaland": "North-East",
    "Tripura": "North-East",
}


def seed_matrix_from_csv() -> int:
    """Load the bundled matrix.csv into sla_matrix_live. Returns rows inserted."""
    rows: list[tuple[str, str, int]] = []
    with MATRIX_CSV.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)  # ['Zone', 'West', 'South', ...]
        col_zones = header[1:]
        for row in reader:
            origin = row[0]
            for col_idx, dest in enumerate(col_zones, start=1):
                days = int(row[col_idx])
                rows.append((origin, dest, days))

    with cursor() as cur:
        cur.execute("DELETE FROM sla_matrix_live")
        cur.executemany(
            "INSERT INTO sla_matrix_live(origin_zone, destination_zone, days) "
            "VALUES (?, ?, ?)",
            rows,
        )
    return len(rows)


def seed_state_zone_fallback() -> int:
    """Populate state→zone fallback table."""
    with cursor() as cur:
        cur.execute("DELETE FROM state_zone_fallback")
        cur.executemany(
            "INSERT INTO state_zone_fallback(state, zone) VALUES (?, ?)",
            list(STATE_ZONE.items()),
        )
    return len(STATE_ZONE)


def seed_pincodes_if_empty() -> None:
    """Load pincode_master.xlsx into pincode_master_live on first run.

    Idempotent — never overwrites an existing master. Delegates the
    Pin/State Name/ODA mapping to edit._replace_live_pincodes() which
    also triggers recompute_all_sla() when n_before == 0.
    """
    # Lazy imports avoid a circular dependency:
    #   seed.py → edit.py → seed.py (for STATE_ZONE / get_live_matrix).
    from app.store.queries import count_pincodes
    if count_pincodes() > 0:
        return   # already loaded — never overwrite

    import pandas as pd

    path = Path(__file__).resolve().parent.parent / "reference" / "pincode_master.xlsx"
    if not path.exists():
        return   # no bundled reference data — silently skip
    df = pd.read_excel(path, sheet_name="Pincode file")

    from app.sections.edit import _replace_live_pincodes
    _replace_live_pincodes(df)


def seed_all_if_empty() -> None:
    """Idempotent seed — only inserts if the live tables are empty."""
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sla_matrix_live")
        if cur.fetchone()[0] == 0:
            seed_matrix_from_csv()
        cur.execute("SELECT COUNT(*) FROM state_zone_fallback")
        if cur.fetchone()[0] == 0:
            seed_state_zone_fallback()
    seed_pincodes_if_empty()


def get_live_matrix() -> dict[tuple[str, str], int]:
    """Return the live matrix as {(origin, destination): days}."""
    with cursor() as cur:
        cur.execute("SELECT origin_zone, destination_zone, days FROM sla_matrix_live")
        return {(r[0], r[1]): r[2] for r in cur.fetchall()}
