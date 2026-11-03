"""Phase 2, step 4: streaming. Watch the graph work instead of waiting for the final answer.

Reuses the same compiled graph from src/jarvis/agent/graph.py - nothing about the graph
itself changes. Only how we READ its output changes: .invoke() vs .stream(...).

Run with:  uv run python examples/phase2_step4_streaming.py
"""

from langchain_core.messages import HumanMessage

from jarvis.agent.graph import build_graph
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

graph = build_graph([get_time, multiply, divide, get_system_info])


# --- stream_mode="updates": one event per node finishing. This is the activity log. ---
print("=== stream_mode='updates' ===")
question = {"messages": [HumanMessage("What time is it, and what is 12 times 12?")]}
for update in graph.stream(question, stream_mode="updates"):
    # `update` is {node_name: {"messages": [...]}} - exactly what that node returned.
    for node_name, change in update.items():
        for msg in change["messages"]:
            kind = type(msg).__name__
            if kind == "AIMessage" and msg.tool_calls:
                print(f"  [{node_name}] model asked for: {[c['name'] for c in msg.tool_calls]}")
            elif kind == "ToolMessage":
                print(f"  [{node_name}] tool result: {msg.content!r}")
            else:
                print(f"  [{node_name}] final answer: {msg.content!r}")


# --- stream_mode="messages": individual tokens as the model writes them. ---
print("\n=== stream_mode='messages' ===")
question = {"messages": [HumanMessage("Say hello in exactly five words.")]}
seen_node = None
pieces = []  # every separate chunk we received, so we can PROVE how many there were
for chunk, metadata in graph.stream(question, stream_mode="messages"):
    seen_node = metadata["langgraph_node"]
    if chunk.content:  # tool-call chunks can be empty text while arguments are built
        pieces.append(chunk.content)

print(f"  Received {len(pieces)} separate chunk(s) from node {seen_node!r}:")
for i, piece in enumerate(pieces):
    print(f"    chunk {i}: {piece!r}")
print("  Joined together:", "".join(pieces))
