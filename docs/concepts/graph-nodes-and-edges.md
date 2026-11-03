# Graph nodes and edges

**One line:** a node is any plain function `(state) -> dict`; an edge says what runs next. Neither cares what's inside the function.

## Why it exists
We tend to think "the tools node" or "the LLM node" as if they're special graph citizens. They
aren't. `add_node`/`add_edge`/`add_conditional_edges` only care about *shape* (a callable that
takes state and returns a dict), never about what the function does inside. That's what lets a
node be an LLM call, a tool runner, a database write, a web request — anything.

## How it works
| Piece | What it really is |
|---|---|
| `add_node(name, fn)` | "When something routes to `name`, call `fn`." |
| `add_edge(A, B)` | **Unconditional.** Whenever `A` finishes, always go straight to `B`. |
| `add_conditional_edges(A, router_fn, mapping)` | After `A` finishes, call `router_fn(state)` — a plain function that returns a **string** — then look that string up in `mapping` to find the real destination. |
| `START` / `END` | Not real nodes. Fixed markers for "where the graph begins/stops". |

**`ToolNode` and `tools_condition` are not special.** They are pre-written node/router functions
LangChain ships so you don't have to write `run_tools`/`has_tool_calls` yourself ([[tool-calling]]).
They are wired in with the exact same `add_node`/`add_conditional_edges` calls as any custom node.

## Adding your own node (e.g. a database / audit-log node)
Same recipe, always:
```python
def save_to_db(state: AgentState) -> dict:
    db.insert(...)       # or: log an audit entry, call an API, read a file - anything
    return {}             # or state changes, if it should affect messages

builder.add_node("save_to_db", save_to_db)
```
Then wire it one of two ways:
- **Always run after some node** → `add_edge("tools", "save_to_db")`
- **Only run sometimes** → `add_conditional_edges("tools", should_save, {"yes": "save_to_db", "no": "chatbot"})`

This is exactly how **Phase 4 (safety)** will work: an `audit_log` node that always runs after
`tools` (`add_edge`), and an `approval` node a conditional edge routes to only when a tool's risk
tier demands it ([[0003-risk-tiers]] - to be written in Phase 4).

## Small example
Proven with a real run (no LLM, fully deterministic) in `examples/phase2_extra_custom_node_wiring.py`:
one router function (`route_after_work`) returns three different destinations (`"loop"`, `"save"`,
`"done"`) across a run, and a custom `save_to_db` node slots in with zero special-casing:
```
did work #1
did work #2
[fake db] saved checkpoint at count=2
did work #3
```

## Alternatives
| Option | Good for | Why we did not pick it (yet) |
|---|---|---|
| `add_edge` / `add_conditional_edges` (this) | Most control flow: fixed step, or a fork between known branches | — |
| `Send()` (dynamic fan-out) | Running a *variable* number of parallel branches (e.g. one sub-task per file found) | Not needed until a tool can return a variable-length list to process in parallel |
| `Command` (node returns its own routing) | Letting a node decide the next node itself, skipping a separate router function | Keeping routing logic separate and visible is clearer while learning |
| Subgraphs (a compiled graph used as one node) | Reusing a whole graph (e.g. a "research" sub-agent) inside a bigger one | No nested agents yet |
| One big node with if/else inside | Very small graphs | Hides the structure; harder to see as a diagram, stream, or resume mid-step |

## Related
- [[tool-calling]]
- [[messages]] (the `add_messages` reducer is one example; `log` here uses `operator.add` instead)
