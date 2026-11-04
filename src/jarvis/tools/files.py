"""List, read, search, write, delete, and move files inside the workspace sandbox.

list_files/read_file/search_files are AUTO: every path is checked by ensure_allowed() first, so
there is nothing beyond .data/workspace/ to protect - the folder allowlist is the real safety
boundary, not the risk tier. write_file is ASK_ONCE: unlike reading, it creates (or silently
overwrites) persistent content - a real, lasting change, even though it is confined to the
sandbox. delete_file/move_file are ALWAYS_ASK - the only truly destructive operations in this
module (a delete cannot be undone; a move/overwrite can destroy what was already there), so every
single call needs its own confirmation, no matter how many times it has been approved before.
"""

import shutil

from langchain_core.tools import tool

from jarvis.safety.paths import WORKSPACE_DIR, ensure_allowed
from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.AUTO)
@tool
def list_files() -> str:
    """List the files in Jarvis's workspace folder."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in WORKSPACE_DIR.iterdir() if p.is_file())
    return "\n".join(names) if names else "(workspace is empty)"


@risk_tier(RiskTier.AUTO)
@tool
def read_file(name: str) -> str:
    """Read a text file's contents from Jarvis's workspace folder."""
    path = ensure_allowed(WORKSPACE_DIR / name)
    if not path.is_file():
        return f"No such file: '{name}'."
    return path.read_text(encoding="utf-8")


@risk_tier(RiskTier.AUTO)
@tool
def search_files(keyword: str) -> str:
    """Search file names and contents in Jarvis's workspace folder for a keyword."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    matches = []
    for path in sorted(WORKSPACE_DIR.iterdir()):
        if not path.is_file():
            continue
        if keyword.lower() in path.name.lower():
            matches.append(path.name)
            continue
        try:
            if keyword.lower() in path.read_text(encoding="utf-8").lower():
                matches.append(path.name)
        except UnicodeDecodeError:
            pass  # skip binary files
    return "\n".join(matches) if matches else f"No files matched '{keyword}'."


@risk_tier(RiskTier.ASK_ONCE)
@tool
def write_file(name: str, content: str) -> str:
    """Create a text file (e.g. a note or reminder) in Jarvis's workspace folder.

    If a file with this name already exists, its content is replaced.
    """
    path = ensure_allowed(WORKSPACE_DIR / name)
    existed = path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"{'Overwrote' if existed else 'Created'} '{name}'."


@risk_tier(RiskTier.ALWAYS_ASK)
@tool
def delete_file(name: str) -> str:
    """Permanently delete a file from Jarvis's workspace folder. Cannot be undone."""
    path = ensure_allowed(WORKSPACE_DIR / name)
    if not path.is_file():
        return f"No such file: '{name}'."
    path.unlink()
    return f"Deleted '{name}'."


@risk_tier(RiskTier.ALWAYS_ASK)
@tool
def move_file(source: str, destination: str) -> str:
    """Move or rename a file in Jarvis's workspace folder.

    Overwrites the destination if it already exists.
    """
    source_path = ensure_allowed(WORKSPACE_DIR / source)
    destination_path = ensure_allowed(WORKSPACE_DIR / destination)
    if not source_path.is_file():
        return f"No such file: '{source}'."
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(destination_path))
    return f"Moved '{source}' to '{destination}'."
