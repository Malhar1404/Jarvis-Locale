# Agent event stream

**One line:** the agent core speaks one small, fixed vocabulary of events; every front-end
(CLI, Qt, voice) only ever needs to understand that vocabulary, never LangGraph itself.

## Why it exists
`CLAUDE.md`'s rule is "`jarvis.agent` never imports `ui`; CLI and Qt are thin front-ends over one
event stream." Before Phase 3, `cli.py` broke the spirit of that rule - it reached directly into
LangGraph's raw stream (`metadata.get("langgraph_node")`, `msg.tool_calls`, `change["messages"]`).
The Qt app would have had to re-learn all of that again. One translator in the middle fixes it.

## How it works
`src/jarvis/agent/events.py` defines a Pydantic union - `Thinking | Token | ToolCall | ToolResult |
Error` (see [[structured-output]] for why Pydantic). `src/jarvis/agent/runner.py`'s `Agent.run(text)`
is the one place that still knows LangGraph: it walks `graph.stream(..., stream_mode=["updates",
"messages"])` (see [[streaming]], [[graph-nodes-and-edges]]) and translates each raw message or
chunk into one of these events. Everything downstream - `cli.py` today, Qt in Phase 6 - only ever
does `match event: case Token(text=text): ...`.

```python
for event in agent.run("what time is it?"):
    match event:
        case Token(text=text):
            print(text, end="")
        case ToolCall(name=name, args=args):
            print(f"[asking for: {name}({args})]")
```

Same principle as `has_tool_calls` returning a plain string instead of the model deciding
anything: a fixed, boring translation step, not intelligence.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Typed `AgentEvent` union (this) | A stable contract between agent and any UI; validated, serializable (`model_dump_json`) | — |
| Let the UI read the raw LangGraph stream (what we had) | Fastest to write once | Breaks the agent/UI boundary; every front-end re-implements the same translation |
| A single `on_event(event: dict)` callback instead of a generator | Push style, fits GUI event loops directly | A generator is simpler to test and to drive from a CLI loop; Qt can still pull from it on a worker thread (Phase 6) |
| LangGraph's own callbacks/tracing (e.g. `BaseCallbackHandler`) | Deep internal instrumentation (LangSmith) | Built for observability tooling, not a small UI-facing vocabulary we control |

## Related
- [[graph-nodes-and-edges]]
- [[streaming]]
- [[structured-output]]
