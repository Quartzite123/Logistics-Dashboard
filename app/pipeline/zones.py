"""Pincode → Zone lookup with State-based fallback."""
from __future__ import annotations

from functools import lru_cache

from ..store.db import cursor


@lru_cache(maxsize=1)
def _state_zone_map() -> dict[str, str]:
    """Load state→zone fallback into memory once per process."""
    with cursor() as cur:
        cur.execute("SELECT state, zone FROM state_zone_fallback")
        return {r[0]: r[1] for r in cur.fetchall()}


def lookup_zone_by_pincode(pincode: str | int | None) -> str | None:
    """Return the zone for a pincode using the live pincode master.

    Returns None if the pincode is missing or not in the master.
    """
    if pincode is None:
        return None
    p = str(pincode).strip()
    if not p or p == "nan":
        return None
    with cursor() as cur:
        cur.execute(
            "SELECT zone FROM pincode_master_live WHERE pincode = ?",
            (p,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def lookup_zone_by_state(state: str | None) -> str | None:
    """Return the zone for an Indian state, or None if unrecognised."""
    if state is None:
        return None
    return _state_zone_map().get(state.strip())


def resolve_zone(pincode: str | int | None, state: str | None) -> str | None:
    """Pincode wins; state is the fallback. Returns None if neither resolves."""
    z = lookup_zone_by_pincode(pincode)
    if z is not None:
        return z
    return lookup_zone_by_state(state)


def clear_caches() -> None:
    """Call after the pincode master is edited."""
    _state_zone_map.cache_clear()
