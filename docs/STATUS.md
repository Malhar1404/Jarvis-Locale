# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-11-04
**Current phase:** Phase 6 (desktop UI) - chat window with the live activity timeline and inline
approval cards is working. User is still editing the Phase 2-5 notes separately.

## Done
- [x] Phase 0: Foundations. See [[phase-00-foundations]].
- [x] Project structure, tooling (ruff, pytest), docs vault, resume system.
- [x] Phase 1, step 1: tools with `@tool` (`src/jarvis/tools/basic.py`), `bind_tools`, reading raw
      `tool_calls` (`examples/phase1_step1_tool_calls.py`). User ran it; works.
- [x] Phase 1, step 2: the manual tool round trip, `ToolMessage` + `tool_call_id`
      (`examples/phase1_step2_tool_roundtrip.py`).
- [x] Phase 1, steps 3-5: system prompts and templates, structured output, `get_system_info`,
      `run_tool` (errors as text), `make_llm`, switch to `qwen3:4b-instruct`.
- [x] Phase 1 notes: `docs/phases/phase-01-tools.md` plus concepts `tool-calling`,
      `prompt-templates`, `structured-output`, `reasoning-models`.
- [x] Phase 2, steps 1-2: `AgentState` + `add_messages` reducer, the hand-built loop
      (`src/jarvis/agent/graph.py`, `has_tool_calls` conditional edge).
- [x] Phase 2, step 3: swapped in the prebuilt `ToolNode` / `tools_condition`.
- [x] Phase 2, step 4: streaming (`"updates"` vs `"messages"`), proved real token chunks arrive.
- [x] Phase 2, step 5: compared our `build_graph` against `langchain.agents.create_agent`.
- [x] Phase 2 extras: a custom `save_to_db` node with a 3-way router; a real streaming CLI chat
      (`src/jarvis/cli.py`, `uv run python -m jarvis`).
- [x] Phase 2 notes drafted: `docs/phases/phase-02-agent-loop.md` plus concept
      `multi-agent-systems` (deterministic routing vs. agents-as-tools with `create_agent`).
- [x] Phase 3, step 1: `AgentEvent` union - `Thinking`/`Token`/`ToolCall`/`ToolResult`/`Error`
      (`src/jarvis/agent/events.py`).
- [x] Phase 3, step 2: `Agent.run(text) -> Iterator[AgentEvent]`, translating the real stream
      (`src/jarvis/agent/runner.py`). Fixed `ToolMessage` missing `name=` in `run_tool` along the way.
- [x] Phase 3, step 3: rewired `cli.py` onto `Agent.run()` - no LangGraph imports left in the CLI.
- [x] Phase 3 notes drafted: `docs/phases/phase-03-events.md` plus concept `agent-event-stream`.
- [x] Phase 4, step 1: risk tiers - `RiskTier` enum, `@risk_tier` decorator, fail-safe default
      (`src/jarvis/safety/tiers.py`).
- [x] Phase 4, step 2: `interrupt()`/`Command(resume=...)` in isolation; proved nodes rerun from
      the top on resume (`examples/phase4_step2_interrupt_mechanics.py`).
- [x] Phase 4, step 3: the real approval gate (`src/jarvis/safety/approval.py`). Found and fixed a
      real duplicate-tool-execution bug caused by the replay behavior (two-pass decide/run split).
- [x] Phase 4, step 4: wired into `Agent.run()`/`Agent.resume()` and the CLI with a live model;
      `ApprovalRequest` joins the `AgentEvent` union.
- [x] Phase 4, step 5: append-only audit log, one JSONL line per decision
      (`src/jarvis/safety/audit.py`, `.data/audit.log`).
- [x] Phase 4 notes drafted: `docs/phases/phase-04-safety.md` plus concepts `risk-tiers`,
      `interrupt-and-resume`, `audit-log`. Folder allowlists and prompt injection/untrusted
      content deferred to Phase 5, where real file/web tools exist to apply them to.
- [x] Phase 5, step 1: folder allowlist (`.data/workspace/`) + real `open_app` tool
      (`src/jarvis/safety/paths.py`, `src/jarvis/tools/apps.py`).
- [x] Phase 5, step 2: volume/brightness control (AUTO). Found and fixed a COM threading bug -
      LangGraph runs tool code on a worker thread; pycaw needed `CoInitialize()` there too.
- [x] Phase 5, step 3: clipboard read (ASK_ONCE) / write (AUTO), using pywin32.
- [x] Phase 5, step 4: list/read/search files in the workspace sandbox (AUTO).
- [x] Phase 5, step 5: `write_file` - create/overwrite notes (ASK_ONCE).
- [x] Phase 5, step 6: Google Sheets timesheet tools (`src/jarvis/tools/timesheet.py`) - the
      agent's first external API integration. Moved a service-account key out of the workspace
      sandbox after realizing the file tools could have read it. Found and fixed a duplicate-row
      bug caused by small-model sentence-parsing ambiguity (docstring fix, not a code workaround).
- [x] Phase 5, step 7: `delete_file` / `move_file` (ALWAYS_ASK) - the only destructive local ops.
- [x] Phase 5 notes drafted: `docs/phases/phase-05-real-tools.md` plus concept
      `folder-allowlist`. Web search and shell deferred as small follow-ups later.
- [x] Phase 6, step 1: `jarvis/setup.py` - pulled the tool list/`SYSTEM_PROMPT` out of `cli.py`
      so the CLI and the Qt UI share one place that builds the `Agent`.
- [x] Phase 6, step 2: `PySide6-Essentials` added (not the full `pyside6` meta-package - that
      pulls in QtWebEngine, ~125MB we don't need). Main window with a worker `QThread` running
      `Agent.run()`/`resume()`, talking to the GUI thread only through signals/slots
      (`src/jarvis/ui/worker.py`, `src/jarvis/ui/main_window.py`). Run with
      `uv run python -m jarvis.ui`.
- [x] Phase 6, step 3: dark "HUD" theme (`src/jarvis/ui/theme.py`) and a card-based live
      activity timeline (`src/jarvis/ui/timeline.py`, `src/jarvis/ui/cards.py`) replacing a
      single text log - a user message, Jarvis's reply, each tool call/result, and an error are
      each their own widget. An `ApprovalRequest` renders as an inline card with real Yes/No
      buttons (no OS popup), and a bouncing-dots card shows while waiting on the model or a
      tool. Window opens maximized.
- [x] Phase 6, step 4: status bar (`QMainWindow.statusBar()`) showing the live turn state on the
      left and the model name on the right; a generated system tray icon (`src/jarvis/ui/tray.py`)
      - closing the window now hides to the tray instead of quitting, with a Show/Hide/Quit menu.

## Next step
1. User reads and rewrites the "my own words" sections of `phase-02-agent-loop.md` through
   `phase-05-real-tools.md`, and lists questions; Claude answers them. Then commit the notes.
2. Continue Phase 6: a side panel listing available tools, highlighting the one in use. After
   that, the UI is in good shape to wire up voice (Phase 7).

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
- `uv run jarvis` can be blocked by Windows Application Control (unsigned generated exe shim).
  Use `uv run python -m jarvis` instead - same code, trusted launcher.
