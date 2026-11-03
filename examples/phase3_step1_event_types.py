"""Phase 3, step 1: the AgentEvent types - no LLM, no graph, just the shapes themselves.

Run with:  uv run python examples/phase3_step1_event_types.py
"""

from jarvis.agent.events import AgentEvent, Error, Thinking, Token, ToolCall, ToolResult

events: list[AgentEvent] = [
    Thinking(node="chatbot"),
    Token(text="The "),
    Token(text="time "),
    Token(text="is "),
    ToolCall(name="get_time", args={}),
    ToolResult(name="get_time", content="14:02", status="ok"),
    ToolResult(name="divide", content="Error: division by zero", status="error"),
    Error(message="example: the LLM call itself failed"),
]

print("A UI only ever needs to branch on `.type` - it never sees LangGraph at all:\n")
for event in events:
    match event:
        case Thinking(node=node):
            print(f"  [thinking] node={node!r} is working...")
        case Token(text=text):
            print(f"  [token]    {text!r}")
        case ToolCall(name=name, args=args):
            print(f"  [tool_call] {name}({args})")
        case ToolResult(status="ok", name=name, content=content):
            print(f"  [tool_ok]  {name} -> {content}")
        case ToolResult(status="error", name=name, content=content):
            print(f"  [tool_err] {name} -> {content}")
        case Error(message=message):
            print(f"  [error]    {message}")

print("\nSame list, proven JSON-serializable (what we'd send over a Qt signal or a websocket):")
print(events[2].model_dump_json())
