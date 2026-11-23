# LangGraph custom stream (progress from inside a tool)

**One line:** a tool can send progress messages to the UI while it is still running, using `get_stream_writer()`.

## Why it exists
A tool returns once, at the end. `inspect_screen` takes ~10 s (capture, then a vision model per
monitor). The Mind panel wants the screenshots the moment they exist, not 10 s later.

## How it works
1. The graph is streamed with `stream_mode=["updates", "messages", "custom"]`.
2. Inside the tool: `writer = get_stream_writer(); writer({"type": "screen_captured", ...})`.
3. The runner receives `("custom", payload)` and turns the dict into a typed event
   (`ScreenCaptured`, `VisionResult`) with `_custom_event()`.
4. Unknown or broken payloads are **dropped** - a progress display must never break a turn.

Why plain **dicts** from tools: `jarvis.tools` then never imports `jarvis.agent` (the architecture rule).
Why it is safe to call anywhere: outside a graph there is no writer, so the helper catches
`RuntimeError` (no runnable) **and `KeyError`** (a plain `tool.invoke()` has a config but no LangGraph
runtime - we found this one when a test failed).

## Small example
```python
def _report(payload: dict) -> None:
    try:
        writer = get_stream_writer()
    except (RuntimeError, KeyError):
        return                      # nobody is listening (a test, a script)
    writer(payload)
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Return everything at the end | simplest | no live feedback for 10 s |
| Split into several tools | each step visible as a normal tool call | the model would have to chain them; 4B models do that badly |
| Callback handlers / `astream_events` | detailed tracing | heavier than one small dict |
| A shared queue/global the UI polls | works anywhere | hidden coupling between tools and UI |
| Streaming vision output as tokens | very live | the vision call is one blocking request per monitor |

## Related
- [[agent-event-stream]]
- [[streaming]]
- [[phase-07b-hud]]
