# interrupt() and resume

**One line:** a checkpointer lets a graph pause mid-node and come back later exactly where it left off.

## Why it exists
Our graph had no memory between calls before Phase 4 - no way to stop and wait for a human. A
[[risk-tiers|risk tier]] of `ask_once`/`always_ask` needs exactly that: freeze the agent, show the
user the exact action, and do nothing until they answer.

## How it works
| Piece | What it does |
|---|---|
| `checkpointer` (e.g. `InMemorySaver()`) | Saves a snapshot of graph state after every step, keyed by `thread_id` |
| `thread_id` (`config={"configurable": {"thread_id": ...}}`) | Which conversation's snapshots to use - a save-file slot |
| `interrupt(payload)` | Called inside a node. Freezes the whole graph there; `.stream()`/`.invoke()` returns normally with a `"__interrupt__"` key holding `payload` |
| `Command(resume=value)` | Passed instead of new input on the next call with the same `thread_id`. The paused node resumes, and `interrupt(...)` returns `value` |

```python
result = graph.invoke({"count": 0}, config=config)
# {'count': 0, '__interrupt__': [Interrupt(value='Increment the counter?', id='...')]}
result = graph.invoke(Command(resume="yes"), config=config)
# {'count': 1}
```

**The gotcha, proven in `examples/phase4_step2_interrupt_mechanics.py`:** on resume, the node
function **reruns from the top**, not from the exact line. `interrupt()` just returns the cached
answer instead of pausing again. Anything with a side effect *before* `interrupt()` in the same
node runs **twice**.

**A real bug this caused:** a node processing two tool calls - an `auto` one, then one needing
approval - ran the `auto` one, paused on the second, then reran *both* on resume: the `auto` call
executed twice for real (proven in `examples/phase4_step3_approval_gate.py`, a counting tool went
from 1 to 2). The fix (`jarvis/safety/approval.py`): **two passes**. Pass 1 (`decide()`) only ever
calls `interrupt()` - no side effects, safe to replay. Pass 2 only starts once every approval in
the batch is resolved, so nothing in it can trigger another pause - each tool, and each
[[audit-log|audit log]] write, runs exactly once.

## Alternatives
| Option | Good for | Why we did not pick it (yet) |
|---|---|---|
| `InMemorySaver` (this) | Isolating the pause/resume mechanism itself | Lost on restart - fine for one CLI session |
| `SqliteSaver` | Surviving an app restart mid-approval | More moving parts to learn at once; Phase 8 (memory) is where persistent, cross-restart state belongs |
| `Send()` per-call fan-out | Each tool call as its own isolated, independently-cached task | Would also avoid the replay bug, but far more machinery than a two-pass loop for our tool-call counts |
| No pause - just refuse risky actions outright | Simpler | Can't do the task at all, even with permission - the whole point is asking, not blocking |

## Related
- [[risk-tiers]]
- [[audit-log]]
- [[graph-nodes-and-edges]]
