# Tool calling

**One line:** the model writes a request ("call `multiply` with a=3, b=4"); our code runs it and sends the result back.

## Why it exists
A model can only produce text. It cannot check the clock, read a file or open an app. Tool calling
is the safe bridge: the model *asks*, our code *decides and acts*. That gap is where permissions live (Phase 4).

**Example:** a waiter writes your order, the kitchen cooks, the waiter brings the food. The waiter never cooks.

## How it works
```
1. We send:    question + list of tools (name, description, argument schema)
2. Model says: AIMessage with tool_calls=[{name, args, id}]    (content is often empty)
3. We run the tool and send back a ToolMessage(content=result, tool_call_id=id)
4. Model reads the result and writes the final answer
```
- The model only sees the tool's **name**, **docstring** and **type hints**, never the Python code.
  A good docstring is what makes the model pick the right tool.
- `tool_call_id` ties each result to its request. Several tools can be requested in one reply.
- The model decides whether to use a tool. It can also skip one it should have used.
- **Errors are normal.** `run_tool` catches unknown tools, bad arguments and crashes and returns
  them as a `ToolMessage(status="error")`, so the model can explain or retry. The assistant never crashes.

## Small example
```python
llm = make_llm().bind_tools([get_time, multiply])
ai = llm.invoke("What is 6 times 7?")      # ai.tool_calls -> [{'name': 'multiply', 'args': {'a': 6, 'b': 7}, ...}]
msg = run_tool(ai.tool_calls[0], tools_by_name)
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Prompt-only ReAct (model writes `Action: ...`, we parse text) | Models without tool support | Fragile parsing |
| Structured output | Getting data in a fixed shape | Extracts data, does not run actions. See [[structured-output]] |
| MCP servers | Ready-made tools shared across apps | Extra moving part; a later stretch goal |
| LangGraph `ToolNode` | Runs tool calls inside a graph | Phase 2. Now we know what it replaces |

## Related
- [[messages]]
- [[chat-model]]
