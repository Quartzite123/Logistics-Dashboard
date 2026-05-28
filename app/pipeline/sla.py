"""SLA / TAT / Variance computation for a single shipment row.

All functions here are pure — they take primitive inputs and the live matrix,
and return the computed values. The pipeline writes the result back to
shipments_latest as the *stored* derived columns (README §19).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ..store.seed import get_live_matrix
from .zones import resolve_zone
from .oda import lookup_oda
from .origin_lookup import resolve_origin_zone


def _to_date(v) -> Optional[date]:
    """Coerce a value to a date, dropping any time component. Returns None on failure."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() == "nan":
            return None
        # Try common formats.
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
        ):
            try:
                return datetime.strptime(s.split(".")[0], fmt).date()
            except ValueError:
                pass
        # Last resort: pandas parser if available
        try:
            import pandas as pd
            ts = pd.to_datetime(s, errors="coerce")
            if ts is not None and not pd_isna(ts):
                return ts.to_pydatetime().date()
        except Exception:
            pass
    return None


def pd_isna(v) -> bool:
    """Tiny null-check that works for numpy NaT/NaN without importing numpy at top level."""
    try:
        import pandas as pd
        return bool(pd.isna(v))
    except Exception:
        return v is None


def actual_tat_days(pickup, delivered, current_status: Optional[str]) -> Optional[int]:
    """Days between Pickup Date and Delivered Date. Date-only subtraction.

    Returns None unless Current Status == 'Delivered' AND both dates parse.
    """
    if current_status != "Delivered":
        return None
    p = _to_date(pickup)
    d = _to_date(delivered)
    if p is None or d is None:
        return None
    return (d - p).days


def expected_tat_days(
    origin_zone: Optional[str],
    destination_zone: Optional[str],
    oda_flag: str,
) -> Optional[int]:
    """Matrix lookup + ODA adjustment. Returns None if either zone missing."""
    if not origin_zone or not destination_zone:
        return None
    matrix = get_live_matrix()
    base = matrix.get((origin_zone, destination_zone))
    if base is None:
        return None
    return base + (1 if oda_flag == "YES" else 0)


def classify_sla(actual: Optional[int], expected: Optional[int]) -> Optional[str]:
    """Return 'Early' / 'On Time' / 'Late', or None if either input is None."""
    if actual is None or expected is None:
        return None
    if actual < expected:
        return "Early"
    if actual == expected:
        return "On Time"
    return "Late"


def compute_row(raw: dict) -> dict:
    """Compute all 7 derived SLA columns for one raw row.

    Input `raw` is a dict keyed by the original display column names
    (e.g. 'Pickup Date', 'Current Status', 'Pin code', 'State', etc.).

    Returns a dict keyed by the derived column names from schema.DERIVED_COLUMNS.
    """
    # Origin zone — resolved via origin_lookup (recents → master exact → fuzzy).
    origin_zone = resolve_origin_zone(raw.get("Origin City"))

    # Destination zone — pincode primary, State fallback.
    dest_zone = resolve_zone(raw.get("Pin code"), raw.get("State"))

    # ODA — pincode primary, default UNKNOWN.
    oda = lookup_oda(raw.get("Pin code"))

    expected = expected_tat_days(origin_zone, dest_zone, oda)
    # TAT clock starts at Manifest Date; fall back to Pickup Date when absent.
    import pandas as pd
    manifest_date = raw.get("Manifest Date")
    start_date = manifest_date if pd.notna(manifest_date) else raw.get("Pickup Date")
    actual = actual_tat_days(
        start_date,
        raw.get("Delivered Date"),
        raw.get("Current Status"),
    )
    variance = (actual - expected) if (actual is not None and expected is not None) else None
    sla = classify_sla(actual, expected)

    return {
        "_origin_zone": origin_zone,
        "_destination_zone": dest_zone,
        "_oda": oda,
        "_expected_tat_days": expected,
        "_actual_tat_days": actual,
        "_tat_variance_days": variance,
        "_sla_status": sla,
    }


