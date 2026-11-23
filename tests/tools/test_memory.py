import pytest

import jarvis.memory.store as store
from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.memory import list_remembered_facts, recall_fact, remember_fact


@pytest.fixture(autouse=True)
def _fresh_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "MEMORY_DB_PATH", tmp_path / "memory.sqlite")
    monkeypatch.setattr(store, "_store", None)
    yield


def test_remember_fact_is_ask_once():
    assert get_risk_tier(remember_fact) == RiskTier.ASK_ONCE


def test_recall_tools_are_auto_tier():
    assert get_risk_tier(recall_fact) == RiskTier.AUTO
    assert get_risk_tier(list_remembered_facts) == RiskTier.AUTO


def test_remember_then_recall_fact():
    result = remember_fact.invoke({"key": "name", "value": "Jatin"})
    assert "Remembered" in result
    assert recall_fact.invoke({"key": "name"}) == "Jatin"


def test_recall_missing_fact_returns_text_not_a_crash():
    assert "Nothing remembered" in recall_fact.invoke({"key": "ghost"})


def test_list_remembered_facts_empty():
    assert "nothing remembered" in list_remembered_facts.invoke({})


def test_list_remembered_facts_lists_everything():
    remember_fact.invoke({"key": "name", "value": "Jatin"})
    remember_fact.invoke({"key": "project_folder", "value": "C:/dev/jarvis"})
    result = list_remembered_facts.invoke({})
    assert "name: Jatin" in result
    assert "project_folder: C:/dev/jarvis" in result
