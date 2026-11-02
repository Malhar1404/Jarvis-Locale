# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-10-30
**Current phase:** Phase 1: Prompts, structured output, and tools (in progress)

## Done
- [x] Phase 0: Foundations. See [[phase-00-foundations]].
- [x] Project structure, tooling (ruff, pytest), docs vault, resume system.
- [x] Phase 1, step 1: tools with `@tool` (`src/jarvis/tools/basic.py`), `bind_tools`, reading raw
      `tool_calls` (`examples/phase1_step1_tool_calls.py`). User ran it; works.
- [x] Phase 1, step 2: the manual tool round trip, `ToolMessage` + `tool_call_id`
      (`examples/phase1_step2_tool_roundtrip.py`).

## Next step
Continue Phase 1:
1. Prompts: `SystemMessage` and `ChatPromptTemplate`. Fixes the "no joke tool" quirk seen in step 1.
2. Structured output: `with_structured_output` with a Pydantic model (extract data, not run actions).
3. Add a `get_system_info` tool; handle tool errors (return the error text to the model).
4. Write the Phase 1 note (`docs/phases/phase-01-tools.md`) and concept notes (`tool-calling`,
   `structured-output`, `prompt-templates`). User edits them in their own words. Then start Phase 2.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
