"""Per-LRN deduplication using lifecycle rank.

Tie-break ladder (README §8.2):
  1. Higher Current Status rank wins
  2. Higher Remarks-progression rank wins
  3. Latest operational timestamp (Last Scan Date, else Delivered, else Pickup) wins
  4. Latest upload batch wins
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd


# README §8.3
STATUS_RANK: dict[str, int] = {
    "Manifested": 1,
    "Dispatched": 2,
    "In Transit": 3,
    "Pending": 4,
    "Delivered": 5,
    "RTO": 5,
}


# README §8.4 — patterns are regexes against the lowercased Remarks string.
# Real data has "reached at destination" with an extra word, so the matcher
# allows optional connectors. Patterns are checked best-rank-first.
REMARKS_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bdelivered\b"), 7),
    (re.compile(r"out for delivery"), 6),
    (re.compile(r"reached\s+(?:at\s+)?destination"), 5),
    (re.compile(r"in transit"), 4),
    (re.compile(r"reached\s+(?:at\s+)?hub"), 3),
    (re.compile(r"dispatched"), 2),
    (re.compile(r"manifested"), 1),
]


def status_rank(s: Optional[str]) -> int:
    if not s:
        return 0
    return STATUS_RANK.get(s.strip(), 0)


def remarks_rank(r: Optional[str]) -> int:
    """Regex match against lowercased Remarks. Highest-rank match wins."""
    if not r:
        return 0
    rl = r.lower()
    best = 0
    for pat, rank in REMARKS_PATTERNS:
        if pat.search(rl) and rank > best:
            best = rank
    return best


def _coerce_ts(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if pd.isna(v):
        return None
    try:
        return pd.to_datetime(v, errors="coerce").to_pydatetime()
    except Exception:
        return None


def _operational_timestamp(row: dict) -> Optional[datetime]:
    """Last Scan Date > Delivered Date > Pickup Date."""
    for col in ("Last Scan Date", "Delivered Date", "Pickup Date"):
        ts = _coerce_ts(row.get(col))
        if ts is not None:
            return ts
    return None


def pick_winner(rows: list[dict]) -> dict:
    """Return the dedup winner of multiple rows sharing the same LRN."""
    if len(rows) == 1:
        return rows[0]

    def sort_key(r):
        return (
            status_rank(r.get("Current Status")),
            remarks_rank(r.get("Remarks")),
            _operational_timestamp(r) or datetime.min,
            r.get("_upload_batch_id") or "",
        )

    return max(rows, key=sort_key)


def merge_into_latest(
    new_rows: list[dict],
    existing_by_lrn: dict[int, dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Merge incoming rows into the existing-latest map.

    Returns (winners_to_insert, winners_to_update, skipped_regressions).
    The caller is responsible for upserting `to_insert + to_update` into shipments_latest
    (or doing the writes inline if it prefers).
    """
    # Group incoming by LRN first (in case the new batch itself contains dups for an LRN)
    new_by_lrn: dict[int, list[dict]] = {}
    for r in new_rows:
        lrn = r.get("LRN")
        if lrn is None:
            continue
        new_by_lrn.setdefault(int(lrn), []).append(r)

    to_insert: list[dict] = []
    to_update: list[dict] = []
    skipped: list[dict] = []

    for lrn, candidates in new_by_lrn.items():
        existing = existing_by_lrn.get(lrn)
        all_candidates = candidates + ([existing] if existing else [])
        winner = pick_winner(all_candidates)

        if existing is None:
            to_insert.append(winner)
        elif winner is existing:
            # Existing already beats every incoming row — no-op.
            skipped.append({"lrn": lrn, "reason": "existing has higher lifecycle rank"})
        else:
            to_update.append(winner)

    return to_insert, to_update, skipped
