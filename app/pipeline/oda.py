"""Pincode → ODA (Out of Delivery Area) lookup.

Until the 22 K pincode master is loaded, this returns 'UNKNOWN' for every
pincode. 'UNKNOWN' is treated as 'NO' for SLA penalty purposes (see README §10.2).
"""
from __future__ import annotations

from ..store.db import cursor


def lookup_oda(pincode: str | int | None) -> str:
    """Return 'YES', 'NO', or 'UNKNOWN'."""
    if pincode is None:
        return "UNKNOWN"
    p = str(pincode).strip()
    if not p or p == "nan":
        return "UNKNOWN"
    with cursor() as cur:
        cur.execute(
            "SELECT oda FROM pincode_master_live WHERE pincode = ?",
            (p,),
        )
        row = cur.fetchone()
    return row[0] if row else "UNKNOWN"
