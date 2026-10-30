# Messages

**One line:** a conversation is a list of typed messages; the model only sees that list.

## Why it exists
LLMs have no memory. "Memory" is just the list we resend each turn.

## How it works
- `SystemMessage`: instructions that set the assistant's role and rules.
- `HumanMessage`: what the user said.
- `AIMessage`: what the model replied. Can carry `tool_calls` (Phase 1).
- `ToolMessage`: the result of running a tool, sent back to the model (Phase 1).

## Related
- [[chat-model]]
