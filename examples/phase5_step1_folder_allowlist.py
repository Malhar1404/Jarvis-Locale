"""Phase 5, step 1: the folder allowlist - checked before any risk tier even runs.

Run with:  uv run python examples/phase5_step1_folder_allowlist.py
"""

from pathlib import Path

from jarvis.safety.paths import WORKSPACE_DIR, ensure_allowed

print(f"Workspace dir: {WORKSPACE_DIR}")

inside = WORKSPACE_DIR / "notes.txt"
print(f"\nInside the workspace: {inside}")
print(" ->", ensure_allowed(inside))

outside = WORKSPACE_DIR / ".." / ".." / "src" / "jarvis" / "safety" / "tiers.py"
print(f"\nOutside, via '..' traversal: {outside}")
try:
    ensure_allowed(outside)
    print(" -> allowed (this would be a bug!)")
except ValueError as exc:
    print(" -> blocked:", exc)

home_ssh = Path.home() / ".ssh" / "id_rsa"
print(f"\nSomewhere else entirely: {home_ssh}")
try:
    ensure_allowed(home_ssh)
    print(" -> allowed (this would be a bug!)")
except ValueError as exc:
    print(" -> blocked:", exc)
