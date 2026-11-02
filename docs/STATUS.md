# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-10-30
**Current phase:** Phase 1 code is done; user is editing the Phase 1 notes. Then start Phase 2.

## Done
- [x] Phase 0: Foundations. See [[phase-00-foundations]].
- [x] Project structure, tooling (ruff, pytest), docs vault, resume system.
- [x] Phase 1, step 1: tools with `@tool` (`src/jarvis/tools/basic.py`), `bind_tools`, reading raw
      `tool_calls` (`examples/phase1_step1_tool_calls.py`). User ran it; works.
- [x] Phase 1, step 2: the manual tool round trip, `ToolMessage` + `tool_call_id`
      (`examples/phase1_step2_tool_roundtrip.py`).

- [x] Phase 1, steps 3-5: system prompts and templates, structured output, `get_system_info`,
      `run_tool` (errors as text), `make_llm`, switch to `qwen3:4b-instruct`.
- [x] Phase 1 notes drafted: `docs/phases/phase-01-tools.md` plus concepts `tool-calling`,
      `prompt-templates`, `structured-output`, `reasoning-models`.

## Next step
1. User reads and rewrites the "my own words" section of `phase-01-tools.md` and lists questions;
   Claude answers them. Then commit the notes.
2. Start Phase 2: the agent loop in LangGraph. First topic: state and nodes (`StateGraph`,
   `add_messages` reducer). Build `llm_node -> tools -> llm_node -> END` by hand, using `make_llm`
   and `run_tool`, then a streaming CLI chat in `src/jarvis/cli.py`.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
