# Streaming

**One line:** getting the reply piece by piece while it is generated instead of waiting for all of it.

## Why it exists
A local 4B model can take seconds to finish. Streaming lets the UI show text (and later speak it)
immediately, and lets us show what the agent is doing live.

## How it works
`for chunk in llm.stream(messages): print(chunk.content, end="")`. In LangGraph (Phase 2) streaming
also has modes for node updates and tokens, which feed the activity timeline in the UI.

## Related
- [[chat-model]]
