"""Origin city lookup tests (LOGIC_UPDATE Change 5)."""
from __future__ import annotations

import pytest

from app.pipeline.origin_lookup import (
    resolve_origin_zone,
    clear_unknown_cities,
    get_unknown_cities,
)


@pytest.fixture(autouse=True)
def _stub_db(monkeypatch):
    """Stub DB-touching helpers so tests run without a real SQLite file."""
    monkeypatch.setattr(
        "app.pipeline.origin_lookup._lookup_recents",
        lambda city_name: None,
    )
    monkeypatch.setattr(
        "app.pipeline.origin_lookup._upsert_recents",
        lambda city_name, state, zone: None,
    )


def test_known_city_exact():
    clear_unknown_cities()
    # Aurangabad is in origin_city_master.csv → West
    assert resolve_origin_zone("Aurangabad") == "West"
    assert "Aurangabad" not in get_unknown_cities()


def test_known_city_case_insensitive():
    clear_unknown_cities()
    assert resolve_origin_zone("aurangabad") == "West"


def test_known_city_fuzzy():
    clear_unknown_cities()
    # Slight misspelling — fuzzy should resolve
    result = resolve_origin_zone("Aurangabd")
    assert result == "West"


def test_unknown_city_returns_none():
    clear_unknown_cities()
    result = resolve_origin_zone("ZZZUnknownCity999")
    assert result is None
    assert "ZZZUnknownCity999" in get_unknown_cities()


def test_none_input():
    assert resolve_origin_zone(None) is None
    assert resolve_origin_zone("") is None


def test_delhi_resolves_north():
    clear_unknown_cities()
    assert resolve_origin_zone("Delhi") == "North"
    assert resolve_origin_zone("New Delhi") == "North"
