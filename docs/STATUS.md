# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-11-04
**Current phase:** Phase 4 code is done; user is editing the Phase 2-4 notes. Then start Phase 5.

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

## Next step
1. User reads and rewrites the "my own words" sections of `phase-02-agent-loop.md`,
   `phase-03-events.md`, and `phase-04-safety.md`, and lists questions; Claude answers them. Then
   commit the notes.
2. Start Phase 5: real PC tools, in order of risk - open apps, volume/brightness, clipboard,
   list/read/search files in allowed folders (folder allowlists), create notes/reminders,
   create/move/delete files (gated), web search (untrusted output), shell (always gated). Each
   tool gets a correct risk tier using what Phase 4 built.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
- `uv run jarvis` can be blocked by Windows Application Control (unsigned generated exe shim).
  Use `uv run python -m jarvis` instead - same code, trusted launcher.
