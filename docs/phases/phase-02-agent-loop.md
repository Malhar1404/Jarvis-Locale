# Phase 2: The agent loop in LangGraph

**Status:** done
**Date:** 2026-11-03

## Goal
Build the ReAct loop (`llm_node -> tools -> llm_node -> ... -> END`) by hand with `StateGraph`,
understand exactly how routing and streaming work, then compare against the prebuilt
`create_agent` to see what it automates and what it hides.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | `AgentState` (`TypedDict` + `add_messages` reducer), a single-node graph | `src/jarvis/agent/state.py`, `examples/phase2_step1_single_node_graph.py` |
| 2 | The real loop by hand: `has_tool_calls` conditional edge, `chatbot <-> tools` | `src/jarvis/agent/graph.py`, `examples/phase2_step2_...py` |
| 3 | Swap our hand-written tool runner for the prebuilt `ToolNode` / `tools_condition` | `examples/phase2_step3_prebuilt_toolnode.py` |
| 4 | Streaming: `stream_mode="updates"` vs `"messages"`, proving real token-by-token chunks arrive | `examples/phase2_step4_streaming.py` |
| 5 | `langchain.agents.create_agent` side-by-side with `build_graph` on the same question | `examples/phase2_step5_create_agent.py` |
| extra | A custom `save_to_db` node wired into the loop; a router returning 3 destinations | `examples/phase2_extra_custom_node_wiring.py` |
| extra | Real streaming CLI chat (manual `history` list, no checkpointer yet) | `src/jarvis/cli.py`, run via `uv run python -m jarvis` |

## Concepts learned
- [[graph-nodes-and-edges]]
- [[streaming]]
- [[multi-agent-systems]] (came out of comparing our custom router to `create_agent`)
- Earlier: [[tool-calling]], [[messages]]

## How it works (my own words)
_Write this yourself. Explain the loop as if telling a friend: what state carries between turns,
how a conditional edge decides "call a tool" vs "stop and answer," and what `create_agent`
actually builds for you under the hood (hint: not more nodes per tool - see [[multi-agent-systems]]
and [[graph-nodes-and-edges]])._

## Things we noticed (real findings, not theory)
- `stream_mode="updates"` only fires once a node fully finishes - looked identical to a slow
  `invoke()` when just printing concatenated text. Switching to `"messages"` (token-level chunks)
  made real streaming visible: multiple distinct chunks, each with its own `langgraph_node` metadata.
- `create_agent` always builds exactly one `"model"` node and at most one `"tools"` node, no matter
  how many tools are passed - all tools share one lookup-by-name node, same as our own
  `tools_by_name` dict. The thing that *does* add nodes is `middleware` (one set of
  before/after hooks per middleware object), which we have not used yet.
- `create_agent` has no way to express a deterministic, non-LLM routing rule (e.g. "always route
  billing questions to this node"). Reaching that with `create_agent` means either dropping to a
  raw `StateGraph` (what we did) or wrapping specialist agents as tools and letting the LLM choose
  the route - a real reliability tradeoff, not just a style choice.
- `uv run jarvis` (the generated console-script exe) was blocked by Windows Application Control.
  `uv run python -m jarvis` runs the identical code through the already-trusted interpreter instead.

## What confused me / questions I still have
-

## Code to look at
- `src/jarvis/agent/graph.py`: the reusable agent core - `build_graph(tools)`.
- `src/jarvis/cli.py`: the first real, interactive front-end over that graph.
- `docs/visuals/phase2-agent-loop-flow.html`: animated walkthrough of the loop, the custom node, and streaming.

## Next
[[PLAN]] Phase 3: turning the raw stream into our own typed `AgentEvent`s.
