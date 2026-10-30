# Messages

**One line:** a conversation is a list of typed messages; the model only sees that list.

## Why it exists
LLMs have no memory. "Memory" is just the list we resend each turn.

## How it works
- `SystemMessage`: instructions that set the assistant's role and rules.
- `HumanMessage`: what the user said.
- `AIMessage`: what the model replied. Can carry `tool_calls` (Phase 1).
- `ToolMessage`: the result of running a tool, sent back to the model (Phase 1).

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Plain dicts `{"role": "user", "content": "..."}` | Quick scripts, OpenAI-style APIs | LangChain accepts them too, but typed messages are safer for tool calls |
| Anthropic / OpenAI native message formats | Using those SDKs directly | LangChain converts to them for us |

## Related
- [[chat-model]]
