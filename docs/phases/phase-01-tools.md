# Phase 1: Prompts, structured output, and tools

**Status:** done
**Date:** 2026-11-02

## Goal
Understand tool calling without any framework hiding it, and learn the two other basic ways to
control a model: system prompts and structured output.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | `@tool` functions, `bind_tools`, read raw `tool_calls` | `src/jarvis/tools/basic.py`, `examples/phase1_step1_tool_calls.py` |
| 2 | The manual round trip: run the tool, send a `ToolMessage` back | `examples/phase1_step2_tool_roundtrip.py` |
| 3 | System prompt, `ChatPromptTemplate`, the `prompt \| llm` chain | `examples/phase1_step3_prompts.py` |
| 4 | `with_structured_output` with Pydantic (extract data, classify) | `examples/phase1_step4_structured_output.py` |
| 5 | `get_system_info` tool, `run_tool` (errors as text), `make_llm` | `src/jarvis/tools/runner.py`, `src/jarvis/llm.py` |

## Concepts learned
- [[tool-calling]]
- [[prompt-templates]]
- [[structured-output]]
- [[reasoning-models]]
- Earlier: [[chat-model]], [[messages]], [[streaming]]

## How it works (my own words)
_Write this yourself. Explain the tool round trip as if telling a friend: who asks, who runs,
what is sent back, and why the `tool_call_id` matters._

## Things we noticed (real findings, not theory)
- With no system prompt the model said "I don't have a joke tool" before answering. A system prompt fixed it.
- The 4B model was good at extracting a reminder but bad at classifying intent (3 of 4 wrong).
  Vague field descriptions did not help. Small models need clearer definitions or examples.
- Asked to "divide 10 by 0", the model skipped the tool and answered from its own knowledge.
- The plain `qwen3:4b` tag is a thinking-only model. Its thoughts leaked into replies and
  `reasoning=False` was ignored. We switched to `qwen3:4b-instruct`. See [[0002-local-model-qwen3-4b]].

## What confused me / questions I still have
- 

## Code to look at
- `src/jarvis/tools/runner.py`: the first piece of "real" agent code. Phase 2 automates this loop.
- `src/jarvis/llm.py`: one place that builds the model.

## Next
[[PLAN]] Phase 2: the agent loop in LangGraph.
