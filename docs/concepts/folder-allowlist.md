# Folder allowlist

**One line:** a file tool may only touch paths inside a fixed set of folders - checked in Python, before the risk tier even runs.

## Why it exists
A [[risk-tiers|risk tier]] controls *whether* a call needs approval. It says nothing about
*where* a file tool is allowed to look at all. Without a separate check, a perfectly "approved"
`read_file` call could still be pointed at `C:\Users\you\.ssh\id_rsa` - the user saying "yes" to
the tool running doesn't make an arbitrary path safe to read.

## How it works
```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = PROJECT_ROOT / ".data" / "workspace"
ALLOWED_FOLDERS = [WORKSPACE_DIR]

def ensure_allowed(path: Path) -> Path:
    resolved = path.resolve()
    if any(resolved.is_relative_to(folder.resolve()) for folder in ALLOWED_FOLDERS):
        return resolved
    raise ValueError(f"'{path}' is outside the allowed folder(s)")
```
Every file tool calls `ensure_allowed(WORKSPACE_DIR / name)` **before** touching the filesystem.
`Path.resolve()` collapses `..` segments, so `"../../src/jarvis/safety/tiers.py"` resolves to its
real location outside `WORKSPACE_DIR` and is rejected - proven directly in
`examples/phase5_step1_folder_allowlist.py` against both a `..` traversal and an unrelated path
(`~/.ssh`).

**A credential is not a path check, but the same principle applies:** the Google Sheets service
account key (Phase 5's timesheet tool) was briefly saved inside `.data/workspace/` - the exact
folder the file tools can freely read. `list_files`/`read_file` would have been able to surface a
real private key in a conversation. The fix was the same idea as the folder allowlist in reverse:
put the credential somewhere the agent's own tools are *not* allowed to reach
(`.data/google_service_account.json`, outside the sandbox).

**The external-resource version of the same idea:** the timesheet tools don't take a spreadsheet
ID as an argument at all - `TIMESHEET_SPREADSHEET_ID` is a fixed constant in `config.py`. The
model can ask to read/write *within* that one sheet, but can never be asked (by a user, or by
injected content) to point the tool at a different spreadsheet. Same shape as a folder allowlist,
just for one external document instead of a folder tree.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Resolve + `is_relative_to()` against a fixed list (this) | Simple, a few lines, easy to test | — |
| Ask the model nicely in the system prompt ("only touch this folder") | Zero code | `CLAUDE.md`: permissions enforced in Python, never only in the prompt - a model can be talked out of a prompt rule |
| OS-level sandboxing (e.g. a restricted user account, container) | Strong isolation regardless of code bugs | Heavy setup for a learning project; our Python check is enough while the agent runs as the same user as us |
| Per-tool hardcoded single path (no general allowlist) | Maximum restriction | Too rigid once more than one tool/folder is involved - the Google Sheets case still needed its own "one resource" scoping, just not expressed as a folder |

## Related
- [[risk-tiers]]
- [[interrupt-and-resume]]
