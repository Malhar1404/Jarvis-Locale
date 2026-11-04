"""Folder allowlist: file tools may only touch paths inside these folders - checked in Python,
before any risk tier even runs. CLAUDE.md: "Permissions are enforced in Python (safety/), never
only in the prompt."

A risk tier controls WHETHER a call needs approval; this controls WHERE a file tool is allowed
to look at all, regardless of approval. A list_files call could otherwise be pointed at
C:\\Users\\you\\.ssh - the model asking nicely does not make that safe.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = PROJECT_ROOT / ".data" / "workspace"

ALLOWED_FOLDERS = [WORKSPACE_DIR]


def ensure_allowed(path: Path) -> Path:
    """Resolve `path` and raise ValueError if it falls outside every allowed folder.

    Returns the resolved path so callers always use the checked version, not the raw input.
    """
    resolved = path.resolve()
    if any(resolved.is_relative_to(folder.resolve()) for folder in ALLOWED_FOLDERS):
        return resolved
    allowed = ", ".join(str(f) for f in ALLOWED_FOLDERS)
    raise ValueError(f"'{path}' is outside the allowed folder(s): {allowed}")
