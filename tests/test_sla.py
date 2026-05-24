"""SLA / TAT acceptance tests (README §23.2)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from app.pipeline.sla import (
    actual_tat_days,
    expected_tat_days,
    classify_sla,
)


# --- actual_tat_days -------------------------------------------------------

def test_actual_tat_basic():
    pickup = datetime(2025, 12, 1, 10, 0)
    delivered = datetime(2025, 12, 5, 16, 30)
    assert actual_tat_days(pickup, delivered, "Delivered") == 4


def test_actual_tat_same_day_pickup_and_delivery():
    pickup = datetime(2025, 12, 1, 10, 0)
    delivered = datetime(2025, 12, 1, 22, 30)
    assert actual_tat_days(pickup, delivered, "Delivered") == 0


def test_actual_tat_strips_time_across_midnight():
    pickup = datetime(2025, 12, 1, 23, 55)
    delivered = datetime(2025, 12, 2, 0, 5)
    assert actual_tat_days(pickup, delivered, "Delivered") == 1


def test_actual_tat_none_if_not_delivered():
    pickup = datetime(2025, 12, 1)
    delivered = datetime(2025, 12, 5)
    assert actual_tat_days(pickup, delivered, "In Transit") is None


def test_actual_tat_none_if_missing_date():
    assert actual_tat_days(None, datetime(2025, 12, 5), "Delivered") is None
    assert actual_tat_days(datetime(2025, 12, 1), None, "Delivered") is None


# --- expected_tat_days -----------------------------------------------------

@patch("app.pipeline.sla.get_live_matrix")
def test_expected_tat_diagonal_no_oda(mock_matrix):
    mock_matrix.return_value = {
        ("West", "West"): 4,
        ("West", "South"): 6,
    }
    assert expected_tat_days("West", "West", "NO") == 4


@patch("app.pipeline.sla.get_live_matrix")
def test_expected_tat_oda_adds_one(mock_matrix):
    mock_matrix.return_value = {("West", "South"): 6}
    assert expected_tat_days("West", "South", "YES") == 7


@patch("app.pipeline.sla.get_live_matrix")
def test_expected_tat_unknown_oda_no_penalty(mock_matrix):
    mock_matrix.return_value = {("West", "South"): 6}
    assert expected_tat_days("West", "South", "UNKNOWN") == 6


@patch("app.pipeline.sla.get_live_matrix")
def test_expected_tat_missing_zone(mock_matrix):
    mock_matrix.return_value = {("West", "South"): 6}
    assert expected_tat_days(None, "South", "NO") is None
    assert expected_tat_days("West", None, "NO") is None
    # Zone present but matrix has no entry for the pair
    assert expected_tat_days("West", "East", "NO") is None


# --- classify_sla ----------------------------------------------------------

def test_classify_early():
    assert classify_sla(actual=3, expected=5) == "Early"


def test_classify_on_time():
    assert classify_sla(actual=5, expected=5) == "On Time"


def test_classify_late():
    assert classify_sla(actual=7, expected=5) == "Late"


def test_classify_null_inputs():
    assert classify_sla(None, 5) is None
    assert classify_sla(5, None) is None
    assert classify_sla(None, None) is None


def test_same_day_delivery_is_early():
    """Pickup == Delivered → Actual=0; Expected from matrix ≥ 4 → Early."""
    with patch("app.pipeline.sla.get_live_matrix") as mock_matrix:
        mock_matrix.return_value = {("West", "West"): 4}
        actual = 0
        expected = expected_tat_days("West", "West", "NO")
        assert classify_sla(actual, expected) == "Early"
