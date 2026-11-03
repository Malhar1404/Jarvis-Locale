# Phase 3: Seeing what the agent does (events and observability)

**Status:** done
**Date:** 2026-11-03

## Goal
Turn the raw LangGraph stream into our own typed events, so any front-end (CLI today, Qt later)
can render "what the agent is doing" without knowing LangGraph exists.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | `AgentEvent` union: `Thinking`, `Token`, `ToolCall`, `ToolResult`, `Error` (Pydantic) | `src/jarvis/agent/events.py`, `examples/phase3_step1_event_types.py` |
| 2 | `Agent.run(text) -> Iterator[AgentEvent]`, translating the real stream | `src/jarvis/agent/runner.py`, `examples/phase3_step2_agent_run.py` |
| 3 | Rewired `cli.py` onto `Agent.run()` - no more LangGraph imports in the CLI | `src/jarvis/cli.py` |

## Concepts learned
- [[agent-event-stream]]
- Earlier: [[graph-nodes-and-edges]], [[streaming]], [[structured-output]]

## How it works (my own words)
_Write this yourself. Explain why the CLI used to "know too much," what changed, and what
`match`/`case` on `AgentEvent` buys us when Qt arrives in Phase 6._

## Things we noticed (real findings, not theory)
- `ToolMessage` has a `name` field that `run_tool` (from Phase 1) never set. It didn't matter
  until `ToolResult` needed the tool's name - a real example of a gap in "working" code that only
  shows up once something downstream actually reads that field.
- Moving the translation into `Agent.run()` made `cli.py` shrink and lose every LangChain/LangGraph
  import except the tool list - a concrete, not just theoretical, confirmation of the
  `jarvis.agent` / `ui` boundary from `CLAUDE.md`.
- `Thinking` events fire once per node per turn (we track `announced_nodes`) rather than once per
  token - useful later for a UI spinner, too noisy to print in the CLI as-is.

## What confused me / questions I still have
-

## Code to look at
- `src/jarvis/agent/events.py`: the whole public vocabulary, in one short file.
- `src/jarvis/agent/runner.py`: `Agent.run()` - the only file that still imports LangGraph internals.
- `src/jarvis/cli.py`: compare against the Phase 2 version in git history - note what's gone.

## Next
[[PLAN]] Phase 4: safety and human-in-the-loop (checkpointers, `interrupt()`, risk tiers,
approval flow in the CLI). `ApprovalRequest` joins the `AgentEvent` union here.
