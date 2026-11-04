# Phase 5: Real PC tools

**Status:** done (web search and shell deferred - see Next)
**Date:** 2026-11-04

## Goal
Build real, everyday tools with correct risk tiers, using what Phase 4 built. Far exceeded the
"6-8 tasks" target before stopping to close the phase out.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | Folder allowlist (`.data/workspace/` only) + the real `open_app` tool (replacing Phase 4's fake stub) | `src/jarvis/safety/paths.py`, `src/jarvis/tools/apps.py` |
| 2 | Volume and brightness control (AUTO) | `src/jarvis/tools/volume.py`, `src/jarvis/tools/brightness.py` |
| 3 | Clipboard read (ASK_ONCE) / write (AUTO) - tier asymmetry based on privacy | `src/jarvis/tools/clipboard.py` |
| 4 | List/read/search files in the workspace sandbox (AUTO, scoped by the allowlist) | `src/jarvis/tools/files.py` |
| 5 | `write_file` - create/overwrite notes (ASK_ONCE) | `src/jarvis/tools/files.py` |
| 6 | Google Sheets timesheet: list tabs, read a tab, add/merge an entry - the agent's first external API tool | `src/jarvis/tools/timesheet.py` |
| 7 | `delete_file` / `move_file` (ALWAYS_ASK) - the only truly destructive local file ops | `src/jarvis/tools/files.py` |

## Concepts learned
- [[folder-allowlist]]
- Earlier: [[risk-tiers]], [[interrupt-and-resume]], [[audit-log]]

## How it works (my own words)
_Write this yourself. Pick one tool from each risk tier (auto/ask_once/always_ask) and explain,
as if telling a friend, why it got that tier - and walk through what the folder allowlist stops
that a risk tier alone would not._

## Things we noticed (real findings, not theory)
- **COM threading bug:** `pycaw` (volume control) failed with `CoInitialize has not been called`
  the first time it ran through the real agent, even though a standalone script worked fine.
  LangGraph runs tool code on a worker thread, and COM must be initialized on whichever thread
  actually touches it. Reproduced with a bare `ThreadPoolExecutor` before fixing it by calling
  `comtypes.CoInitialize()` (safe to call repeatedly) inside the tool itself.
- **A credential almost ended up somewhere it was readable.** The Google Sheets service account
  key was first saved into `.data/workspace/` - exactly the folder `list_files`/`read_file` can
  freely access. Moved to `.data/google_service_account.json`, outside anything the agent's own
  tools can reach. See [[folder-allowlist]].
- **A duplicate-row bug came from the model, not the code.** Asked to log two different projects
  in one sentence, the small model called `add_timesheet_entry` twice with the *same* project and
  task text, differing only in hours - producing a real `"sklo, sklo"` duplicated row in the
  user's actual sheet. The merge-by-date logic behaved correctly given its input; the ambiguity
  was upstream, in how a small model parses a multi-item sentence (same limitation noted back in
  [[structured-output]], Phase 1). Fixed by tightening the tool's docstring with an explicit
  two-project example, not by adding code to guess the model's intent.
- **Risk tiers are judgment calls, revised in practice.** `read_timesheet_tab` and
  `add_timesheet_entry` started as `ALWAYS_ASK` and were deliberately loosened to `ASK_ONCE` after
  live use - a reminder that a tier is a starting estimate of risk, not a one-time decision.

## What confused me / questions I still have
-

## Code to look at
- `src/jarvis/safety/paths.py`: the whole folder allowlist, in about 20 lines.
- `src/jarvis/tools/timesheet.py`: the first tool reaching a real external account - compare its
  shape (one fixed resource ID, never a model-supplied one) to the local folder allowlist.
- `.data/audit.log`: every real decision made across this phase's live testing is in there.

## Next
[[PLAN]] Web search (untrusted content - deferred again, now waiting on real web tools) and shell
(always gated, the highest-risk tool in the project) remain unbuilt from Phase 5's original list -
add them later as small follow-ups whenever wanted. Next phase: [[PLAN]] Phase 6, the PySide6
desktop UI, consuming the same `AgentEvent` stream the CLI already uses.
