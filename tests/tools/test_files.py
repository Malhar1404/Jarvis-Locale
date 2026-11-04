import pytest

from jarvis.safety.paths import WORKSPACE_DIR
from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.files import list_files, read_file, search_files, write_file


@pytest.fixture(autouse=True)
def _clean_workspace():
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    for path in WORKSPACE_DIR.iterdir():
        if path.is_file():
            path.unlink()
    yield
    for path in WORKSPACE_DIR.iterdir():
        if path.is_file():
            path.unlink()


def test_tools_are_auto_tier():
    assert get_risk_tier(list_files) == RiskTier.AUTO
    assert get_risk_tier(read_file) == RiskTier.AUTO
    assert get_risk_tier(search_files) == RiskTier.AUTO


def test_write_file_is_ask_once():
    assert get_risk_tier(write_file) == RiskTier.ASK_ONCE


def test_list_files_empty():
    assert "empty" in list_files.invoke({})


def test_list_and_read_a_real_file():
    (WORKSPACE_DIR / "note.txt").write_text("remember the milk", encoding="utf-8")
    assert "note.txt" in list_files.invoke({})
    assert read_file.invoke({"name": "note.txt"}) == "remember the milk"


def test_read_missing_file_returns_text_not_a_crash():
    assert "No such file" in read_file.invoke({"name": "ghost.txt"})


def test_read_file_blocks_path_traversal():
    with pytest.raises(ValueError, match="outside the allowed folder"):
        read_file.invoke({"name": "../../src/jarvis/safety/tiers.py"})


def test_search_files_matches_name_and_content():
    (WORKSPACE_DIR / "shopping.txt").write_text("milk and eggs", encoding="utf-8")
    (WORKSPACE_DIR / "other.txt").write_text("nothing relevant", encoding="utf-8")
    assert search_files.invoke({"keyword": "shopping"}) == "shopping.txt"
    assert search_files.invoke({"keyword": "milk"}) == "shopping.txt"
    assert "No files matched" in search_files.invoke({"keyword": "xyz"})


def test_write_file_creates_then_overwrites():
    result = write_file.invoke({"name": "note.txt", "content": "first draft"})
    assert "Created" in result
    assert read_file.invoke({"name": "note.txt"}) == "first draft"

    result = write_file.invoke({"name": "note.txt", "content": "final draft"})
    assert "Overwrote" in result
    assert read_file.invoke({"name": "note.txt"}) == "final draft"


def test_write_file_blocks_path_traversal():
    with pytest.raises(ValueError, match="outside the allowed folder"):
        write_file.invoke({"name": "../escape.txt", "content": "nope"})
