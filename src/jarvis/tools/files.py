"""List, read, and search files inside the workspace sandbox.

AUTO tier for all three: every path is checked by ensure_allowed() first, so there is nothing
beyond .data/workspace/ to protect - the folder allowlist is the actual safety boundary here,
not the risk tier.
"""

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
