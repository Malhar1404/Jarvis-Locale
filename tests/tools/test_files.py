import pytest

from jarvis.safety.paths import WORKSPACE_DIR
from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.files import (
    delete_file,
    list_files,
    move_file,
    read_file,
    search_files,
    write_file,
)


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


def test_delete_and_move_are_always_ask():
    assert get_risk_tier(delete_file) == RiskTier.ALWAYS_ASK
    assert get_risk_tier(move_file) == RiskTier.ALWAYS_ASK


def test_delete_file_removes_it():
    (WORKSPACE_DIR / "note.txt").write_text("bye", encoding="utf-8")
    result = delete_file.invoke({"name": "note.txt"})
    assert "Deleted" in result
    assert "No such file" in read_file.invoke({"name": "note.txt"})


def test_delete_missing_file_returns_text_not_a_crash():
    assert "No such file" in delete_file.invoke({"name": "ghost.txt"})


def test_delete_file_blocks_path_traversal():
    with pytest.raises(ValueError, match="outside the allowed folder"):
        delete_file.invoke({"name": "../../src/jarvis/safety/tiers.py"})


def test_move_file_renames_it():
    (WORKSPACE_DIR / "draft.txt").write_text("hello", encoding="utf-8")
    result = move_file.invoke({"source": "draft.txt", "destination": "final.txt"})
    assert "Moved" in result
    assert "No such file" in read_file.invoke({"name": "draft.txt"})
    assert read_file.invoke({"name": "final.txt"}) == "hello"


def test_move_missing_source_returns_text_not_a_crash():
    assert "No such file" in move_file.invoke({"source": "ghost.txt", "destination": "new.txt"})


def test_move_file_blocks_path_traversal_on_either_side():
    (WORKSPACE_DIR / "draft.txt").write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="outside the allowed folder"):
        move_file.invoke({"source": "draft.txt", "destination": "../escape.txt"})
    with pytest.raises(ValueError, match="outside the allowed folder"):
        move_file.invoke(
            {"source": "../../src/jarvis/safety/tiers.py", "destination": "stolen.txt"}
        )
