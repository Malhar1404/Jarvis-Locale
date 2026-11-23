"""Long-term memory: a handful of small facts about the user that survive across conversations -
separate from the per-thread conversation history in agent/runner.py (that's "what did we just
talk about"; this is "what do I know about you, period"). Backed by LangGraph's own Store
interface, so no new dependency - just a second sqlite file alongside the checkpoint one.

isolation_level=None (autocommit) is required here: SqliteStore runs its own "BEGIN" inside each
call, which collides with sqlite3's default implicit-transaction mode. Checked directly with a
throwaway script before writing this - the error otherwise is "cannot start a transaction within a
transaction", which gives no hint that isolation_level is the fix.
"""

import sqlite3

from langgraph.store.sqlite import SqliteStore

from jarvis.config import MEMORY_DB_PATH

_NAMESPACE = ("user_profile",)
_store: SqliteStore | None = None


def _get_store() -> SqliteStore:
    global _store
    if _store is None:
        MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(MEMORY_DB_PATH), check_same_thread=False, isolation_level=None)
        _store = SqliteStore(conn)
    return _store


def remember(key: str, value: str) -> None:
    """Save (or overwrite) one fact about the user."""
    _get_store().put(_NAMESPACE, key, {"value": value})


def recall(key: str) -> str | None:
    """Look up one fact by key, or None if nothing is remembered under it."""
    item = _get_store().get(_NAMESPACE, key)
    return item.value["value"] if item else None


def recall_all() -> dict[str, str]:
    """Every remembered fact, key -> value."""
    return {item.key: item.value["value"] for item in _get_store().search(_NAMESPACE)}
