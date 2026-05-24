"""Dedup engine acceptance tests (README §23.1)."""
from __future__ import annotations

from datetime import datetime

import pytest

from app.pipeline.dedup import (
    STATUS_RANK,
    status_rank,
    remarks_rank,
    pick_winner,
    merge_into_latest,
)


def _row(**kw) -> dict:
    """Build a dedup-input row with sensible defaults."""
    base = {
        "LRN": 1,
        "Current Status": "In Transit",
        "Remarks": "",
        "Last Scan Date": None,
        "Delivered Date": None,
        "Pickup Date": None,
        "_upload_batch_id": "batch1",
    }
    base.update(kw)
    return base


def test_status_rank_table():
    assert status_rank("Manifested") == 1
    assert status_rank("Dispatched") == 2
    assert status_rank("In Transit") == 3
    assert status_rank("Pending") == 4
    assert status_rank("Delivered") == 5
    assert status_rank("RTO") == 5
    assert status_rank("Unknown") == 0
    assert status_rank(None) == 0


def test_remarks_rank_keywords():
    assert remarks_rank("Delivered to Consignee") == 7
    assert remarks_rank("Out for Delivery") == 6
    # Real data contains "Consignment Reached at Destination" — matcher tolerates
    # the optional "at" connector.
    assert remarks_rank("Consignment Reached at Destination") == 5
    assert remarks_rank("Consignment Reached Destination") == 5
    assert remarks_rank("In Transit to next hub") == 4
    assert remarks_rank("Reached Hub Nagpur") == 3
    assert remarks_rank("Consignment Dispatched from Origin City") == 2
    assert remarks_rank("Unknown remark") == 0
    assert remarks_rank("") == 0


def test_lifecycle_rank_wins():
    r_intransit = _row(LRN=10, **{"Current Status": "In Transit"})
    r_delivered = _row(LRN=10, **{"Current Status": "Delivered"})
    winner = pick_winner([r_intransit, r_delivered])
    assert winner is r_delivered


def test_remarks_breaks_status_tie():
    r1 = _row(LRN=11, **{"Current Status": "In Transit", "Remarks": "Reached Hub"})
    r2 = _row(LRN=11, **{"Current Status": "In Transit", "Remarks": "Out for Delivery"})
    winner = pick_winner([r1, r2])
    assert winner is r2


def test_timestamp_breaks_status_and_remarks_tie():
    r1 = _row(
        LRN=12,
        **{"Current Status": "In Transit", "Remarks": "In Transit",
           "Last Scan Date": datetime(2026, 1, 1)},
    )
    r2 = _row(
        LRN=12,
        **{"Current Status": "In Transit", "Remarks": "In Transit",
           "Last Scan Date": datetime(2026, 2, 1)},
    )
    assert pick_winner([r1, r2]) is r2


def test_regression_blocked():
    """Later-uploaded outdated row must NOT overwrite a more advanced one."""
    existing_delivered = _row(LRN=20, **{"Current Status": "Delivered"})
    new_intransit = _row(LRN=20, **{"Current Status": "In Transit"})
    existing_by_lrn = {20: existing_delivered}
    to_insert, to_update, skipped = merge_into_latest(
        [new_intransit], existing_by_lrn
    )
    assert to_insert == []
    assert to_update == []
    assert len(skipped) == 1
    assert skipped[0]["lrn"] == 20


def test_merge_inserts_new_lrn():
    new_row = _row(LRN=30, **{"Current Status": "Manifested"})
    to_insert, to_update, _ = merge_into_latest([new_row], existing_by_lrn={})
    assert len(to_insert) == 1
    assert to_insert[0]["LRN"] == 30


def test_merge_updates_when_new_wins():
    existing = _row(LRN=40, **{"Current Status": "Dispatched"})
    incoming = _row(LRN=40, **{"Current Status": "Delivered"})
    _, to_update, _ = merge_into_latest([incoming], {40: existing})
    assert len(to_update) == 1
    assert to_update[0]["Current Status"] == "Delivered"
