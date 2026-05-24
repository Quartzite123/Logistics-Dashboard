"""
Origin city → zone resolution.

Lookup chain (in order):
  1. origin_recents table  (SQLite, fast, grows automatically)
  2. origin_city_master.csv  — exact match, case-insensitive
  3. origin_city_master.csv  — fuzzy match (difflib, cutoff 0.80)
  4. Not found — flag for UI warning toast; return None

On every successful resolution from steps 2 or 3, the city is upserted
into origin_recents so future lookups hit step 1.
"""

from __future__ import annotations
import csv
import difflib
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.store.db import cursor

_MASTER_PATH = Path(__file__).parent.parent / "data" / "origin_city_master.csv"


def _normalise_ne(zone: str) -> str:
    """Map 'NE' shorthand → 'North-East' to match DB ZONES constant."""
    return "North-East" if zone.strip().upper() == "NE" else zone.strip()


@lru_cache(maxsize=1)
def _load_master() -> list[dict]:
    """Load origin_city_master.csv once and cache it in memory.

    CSV header is `city,state,region` — we read `region` and store under
    the `zone` key so the rest of the module is zone-keyed.
    """
    rows = []
    with open(_MASTER_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "city":  row["city"].strip(),
                "state": row["state"].strip(),
                "zone":  _normalise_ne(row["region"]),
            })
    return rows


def _lookup_recents(city_name: str) -> Optional[dict]:
    """Check origin_recents table. Returns {city, state, zone} or None."""
    with cursor() as c:
        c.execute(
            "SELECT city_name, state, zone FROM origin_recents WHERE LOWER(city_name) = LOWER(?)",
            (city_name,),
        )
        row = c.fetchone()
        if row:
            return {"city": row[0], "state": row[1], "zone": row[2]}
    return None


def _lookup_master_exact(city_name: str) -> Optional[dict]:
    """Case-insensitive exact match in origin_city_master.csv."""
    needle = city_name.strip().lower()
    for row in _load_master():
        if row["city"].lower() == needle:
            return row
    return None


def _lookup_master_fuzzy(city_name: str) -> Optional[dict]:
    """Fuzzy match in origin_city_master.csv using difflib, cutoff 0.80."""
    master = _load_master()
    city_names = [r["city"] for r in master]
    matches = difflib.get_close_matches(city_name, city_names, n=1, cutoff=0.80)
    if matches:
        matched = matches[0]
        for row in master:
            if row["city"] == matched:
                return row
    return None


def _upsert_recents(city_name: str, state: str, zone: str) -> None:
    """Insert or increment seen_count in origin_recents."""
    today = date.today().isoformat()
    with cursor() as c:
        c.execute(
            """
            INSERT INTO origin_recents (city_name, state, zone, last_seen, seen_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(city_name) DO UPDATE SET
                last_seen  = excluded.last_seen,
                seen_count = seen_count + 1
            """,
            (city_name, state, zone, today),
        )


# Global set — accumulates unknown cities during a single upload run.
# Cleared by the ingest layer before each new upload.
_unknown_cities: set[str] = set()


def clear_unknown_cities() -> None:
    _unknown_cities.clear()


def get_unknown_cities() -> set[str]:
    return set(_unknown_cities)


def resolve_origin_zone(city_name: str | None) -> Optional[str]:
    """
    Main entry point called by sla.compute_row().

    Returns the zone string ('West' | 'South' | 'North' | 'East' | 'North-East')
    or None if the city cannot be resolved.
    """
    if not city_name or str(city_name).strip() in ("", "nan", "None"):
        return None

    city_name = str(city_name).strip()

    # 1 — recents (fast path)
    hit = _lookup_recents(city_name)
    if hit:
        _upsert_recents(city_name, hit["state"], hit["zone"])  # bump seen_count + last_seen
        return hit["zone"]

    # 2 — exact match in master
    hit = _lookup_master_exact(city_name)
    if hit:
        _upsert_recents(city_name, hit["state"], hit["zone"])
        return hit["zone"]

    # 3 — fuzzy match in master
    hit = _lookup_master_fuzzy(city_name)
    if hit:
        _upsert_recents(city_name, hit["state"], hit["zone"])
        return hit["zone"]

    # 4 — unknown: flag for UI warning
    _unknown_cities.add(city_name)
    return None


def invalidate_master_cache() -> None:
    """Call if origin_city_master.csv is replaced at runtime."""
    _load_master.cache_clear()
