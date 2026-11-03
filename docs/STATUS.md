# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-11-03
**Current phase:** Phase 2 code is done; user is editing the Phase 2 notes. Then start Phase 3.

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

## Next step
1. User reads and rewrites the "my own words" section of `phase-02-agent-loop.md` and lists
   questions; Claude answers them. Then commit the notes.
2. Start Phase 3: turn the raw LangGraph stream into our own typed events (`Thinking`, `ToolCall`,
   `ToolResult`, `Token`, `ApprovalRequest`, `Error`) and an `agent.run(text) -> Iterator[AgentEvent]`
   API - this is what the future Qt UI will consume.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
- `uv run jarvis` can be blocked by Windows Application Control (unsigned generated exe shim).
  Use `uv run python -m jarvis` instead - same code, trusted launcher.
