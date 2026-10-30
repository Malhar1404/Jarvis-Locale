# Streaming

**One line:** getting the reply piece by piece while it is generated instead of waiting for all of it.

## Why it exists
A local 4B model can take seconds to finish. Streaming lets the UI show text (and later speak it)
immediately, and lets us show what the agent is doing live.

## How it works
`for chunk in llm.stream(messages): print(chunk.content, end="")`. In LangGraph (Phase 2) streaming
also has modes for node updates and tokens, which feed the activity timeline in the UI.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| `invoke` (no streaming) | Background jobs, batch work | User waits for the full answer; bad for UI and voice |
| `astream` (async streaming) | Async servers and apps | Same idea; we use the sync version first, async later if needed |
| Server-sent events / WebSocket streaming | Web apps | We are a desktop app, so Qt signals do this job |

## Related
- [[chat-model]]
