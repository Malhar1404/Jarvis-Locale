# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-10-30
**Current phase:** Phase 1: Prompts, structured output, and tools (not started)

## Done
- [x] Phase 0: Foundations. See [[phase-00-foundations]].
- [x] Project structure, tooling (ruff, pytest), docs vault, resume system.

## Next step
Start Phase 1. First topic: what a tool call really is.
1. Explain the tool-calling round trip (model asks, our code runs, result goes back).
2. Write `get_time`, `get_system_info`, `calculator` with `@tool` in `src/jarvis/tools/`.
3. In `examples/phase1_tool_calls.py`: bind the tools, print the raw `tool_calls`, run a tool by hand,
   send back a `ToolMessage`, print the final answer.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama and `qwen3:4b` are installed. `examples/phase0_hello_llm.py` works.
