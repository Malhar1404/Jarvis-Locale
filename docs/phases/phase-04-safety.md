# Phase 4: Safety and human-in-the-loop

**Status:** done (folder allowlists and prompt injection/untrusted content moved to Phase 5,
where there will be real file/web tools to apply them to)
**Date:** 2026-11-04

## Goal
Make the agent pause before anything risky, show the exact action, and do nothing until the user
approves - enforced in Python, not just asked for in a prompt.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | Risk tiers: `auto`/`ask_once`/`always_ask`/`never`, a `@risk_tier` decorator, fail-safe default | `src/jarvis/safety/tiers.py`, `examples/phase4_step1_risk_tiers.py` |
| 2 | `interrupt()` / `Command(resume=...)` in isolation - proved the "reruns from the top" behavior | `examples/phase4_step2_interrupt_mechanics.py` |
| 3 | The real approval gate, tying tiers to `interrupt()`; found and fixed a real duplicate-execution bug | `src/jarvis/safety/approval.py`, `examples/phase4_step3_approval_gate.py` |
| 4 | Wired into `Agent.run()`/`Agent.resume()` and the CLI with a live model | `src/jarvis/agent/runner.py`, `src/jarvis/cli.py` |
| 5 | Append-only audit log, one JSONL line per decision | `src/jarvis/safety/audit.py` |

## Concepts learned
- [[risk-tiers]]
- [[interrupt-and-resume]]
- [[audit-log]]
- Earlier: [[agent-event-stream]], [[graph-nodes-and-edges]]

## How it works (my own words)
_Write this yourself. Explain the approval flow end to end as if telling a friend: what happens
from the moment the model asks for a risky tool, through the pause, to the user's yes/no, to the
model finally getting its answer._

## Things we noticed (real findings, not theory)
- `interrupt()` doesn't pause mid-statement - the whole node function **reruns from the top** on
  resume, with earlier `interrupt()` calls in the same node returning their cached answers instead
  of pausing again.
- That gotcha caused a **real bug**, not just a cosmetic one: a tool call that ran *before* a later
  call in the same turn paused the node actually executed **twice** - proven with a counting tool
  (`CALL_COUNTS`) going from 1 to 2. Fixed by splitting the gate into a pure "decide" pass
  (`interrupt()` only, safe to replay) and a second pass that only starts once nothing can pause
  anymore, so execution - and the audit log write - happens exactly once.
- `ask_once` approval is remembered **within a single turn** too, not just across turns: two calls
  to the same tool in one AI reply only trigger one `interrupt()`, because the local `approved`
  set updates before the loop reaches the second call.
- `ToolMessage` had a `name` field nobody was setting (found back in Phase 3) - this phase's audit
  log and `ApprovalRequest` events both depend on it being there.

## What confused me / questions I still have
-

## Code to look at
- `src/jarvis/safety/approval.py`: the whole enforcement point - small, but the two-pass comment
  at the top explains a real bug we hit and fixed.
- `examples/phase4_step3_approval_gate.py`: run it again any time to see all four tiers, plus the
  duplicate-execution regression check, in one place.
- `.data/audit.log`: after running the CLI or the examples, open it - one line per decision made.

## Next
[[PLAN]] Phase 5: real PC tools (in order of risk), including the two topics deferred from this
phase - folder allowlists and treating file/web content as untrusted input.
