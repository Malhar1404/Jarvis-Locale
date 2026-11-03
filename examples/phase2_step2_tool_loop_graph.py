"""Phase 2, step 2: the tools node + conditional edge. This is the real agent loop.

Run with:  uv run python examples/phase2_step2_tool_loop_graph.py
"""

from langchain_core.messages import HumanMessage

from jarvis.agent.graph import build_graph
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

graph = build_graph([get_time, multiply, divide, get_system_info])


def ask(question: str) -> None:
    print(f"\n=== {question}")
    result = graph.invoke({"messages": [HumanMessage(question)]})
    for m in result["messages"]:
        extra = f"  tool_calls={m.tool_calls}" if getattr(m, "tool_calls", None) else ""
        print(f"  {type(m).__name__:13} {str(m.content)[:100]!r}{extra}")


# One tool, like before.
ask("What is 123456 times 654321?")

# Needs the model to use TWO tools, one after another, in two trips through the loop.
# Phase 1's hand-written loop could not do this: it only went around once.
ask("First tell me what time it is, then tell me my current CPU and battery usage.")
