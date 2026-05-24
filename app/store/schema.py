"""Column definitions for the Delhivery 41-column schema, derived SLA columns,
and helpers for translating between display names (with spaces) and DB-safe
snake_case names."""
from __future__ import annotations

import re

# Order matters — matches the Delhivery file column order (A..AO).
RAW_COLUMNS: list[str] = [
    "LRN",                          # A
    "Order id",                     # B — actually Company name
    "No of boxes",                  # C
    "Client",                       # D — useless ('kiirus b2bc')
    "Manifest Date",                # E
    "Pickup Date",                  # F
    "Expected Date",                # G — deprecated (use matrix)
    "Invoice Number",               # H
    "Consignee name",               # I
    "Origin City",                  # J
    "Destination City",             # K
    "Client Location/warehouse",    # L
    "Pick up Address",              # M
    "Pin code",                     # N
    "Dispatch Count",               # O
    "First dispatch date",          # P
    "Last dispatch date",           # Q
    "Last Scan Location",           # R
    "Last Scan Date",               # S
    "Current Status",               # T
    "Status Type",                  # U — ignored for dedup
    "Remarks",                      # V — dedup tie-breaker
    "Promise Date",                 # W
    "Delivered Date",               # X
    "Payment Type",                 # Y
    "Master Waybill",               # Z
    "Additional Remarks",           # AA — POD notes, NOT for dedup
    "Return Promise Date",          # AB
    "Transaction Type",             # AC
    "Transaction Mode",             # AD
    "First Pending Date",           # AE
    "Package Amount",               # AF
    "Weight",                       # AG
    "First attempt date",           # AH
    "Last Attempt date",            # AI
    "Attempt Count",                # AJ
    "First Return Date",            # AK
    "Invoice Zone",                 # AL — Delhivery billing zone, NOT geographic
    "RVP/ Forward identifier",      # AM
    "PUR ID",                       # AN
    "State",                        # AO
]

# Derived SLA columns persisted on shipments_latest (see README §19).
DERIVED_COLUMNS: list[str] = [
    "_origin_zone",
    "_destination_zone",
    "_oda",
    "_expected_tat_days",
    "_actual_tat_days",
    "_tat_variance_days",
    "_sla_status",
]

# All columns whose values are datetimes in the Delhivery export.
DATE_COLUMNS: list[str] = [
    "Manifest Date",
    "Pickup Date",
    "Expected Date",
    "First dispatch date",
    "Last dispatch date",
    "Last Scan Date",
    "Promise Date",
    "Delivered Date",
    "Return Promise Date",
    "First Pending Date",
    "First attempt date",
    "Last Attempt date",
    "First Return Date",
]

# Columns whose values are numeric (used for sql types).
INT_COLUMNS = {"LRN", "No of boxes", "Pin code", "Dispatch Count", "Master Waybill"}
FLOAT_COLUMNS = {
    "Pick up Address", "Transaction Type", "Transaction Mode",
    "Package Amount", "Weight", "Attempt Count",
}


def to_db_col(name: str) -> str:
    """Convert a display column name to a SQLite-safe snake_case identifier.

    Examples:
        "LRN"               -> "lrn"
        "Order id"          -> "order_id"
        "Pick up Address"   -> "pick_up_address"
        "RVP/ Forward identifier" -> "rvp_forward_identifier"
    """
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s


# Pre-built bidirectional mappings.
DB_COL: dict[str, str] = {orig: to_db_col(orig) for orig in RAW_COLUMNS}
DISPLAY_COL: dict[str, str] = {db: orig for orig, db in DB_COL.items()}


def sqlite_type(col: str) -> str:
    """Return the SQLite column type for a raw column name."""
    if col in INT_COLUMNS:
        return "INTEGER"
    if col in FLOAT_COLUMNS:
        return "REAL"
    if col in DATE_COLUMNS:
        # Store dates as ISO strings; SQLite has no native date type.
        return "TEXT"
    return "TEXT"


# Schema for the 5 zones — used in matrix and pincode validation.
ZONES: list[str] = ["West", "South", "North", "East", "North-East"]
