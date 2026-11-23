import pytest

import jarvis.memory.store as store


@pytest.fixture(autouse=True)
def _fresh_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "MEMORY_DB_PATH", tmp_path / "memory.sqlite")
    monkeypatch.setattr(store, "_store", None)
    yield


def test_recall_missing_key_returns_none():
    assert store.recall("name") is None


def test_remember_then_recall_round_trips():
    store.remember("name", "Jatin")
    assert store.recall("name") == "Jatin"


def test_remember_overwrites_existing_value():
    store.remember("name", "Jatin")
    store.remember("name", "J")
    assert store.recall("name") == "J"


def test_recall_all_lists_every_fact():
    store.remember("name", "Jatin")
    store.remember("project_folder", "C:/dev/jarvis")
    assert store.recall_all() == {"name": "Jatin", "project_folder": "C:/dev/jarvis"}


def test_recall_all_empty_is_empty_dict():
    assert store.recall_all() == {}
