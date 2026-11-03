"""Phase 2, step 3: swap our hand-written tools node + condition for LangGraph's prebuilt ones.

Compare this file to src/jarvis/agent/graph.py line by line - the wiring (add_edge,
add_conditional_edges) is identical. Only run_tools/has_tool_calls are replaced.

Run with:  uv run python examples/phase2_step3_prebuilt_toolnode.py
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from jarvis.agent.state import AgentState
from jarvis.llm import make_llm
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

tools = [get_time, multiply, divide, get_system_info]
llm = make_llm().bind_tools(tools)


def chatbot(state: AgentState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


builder = StateGraph(AgentState)
builder.add_node("chatbot", chatbot)
builder.add_node("tools", ToolNode(tools))  # <- was our run_tools

builder.add_edge(START, "chatbot")
# tools_condition returns "tools" or END directly: no dict mapping needed.
builder.add_conditional_edges("chatbot", tools_condition)  # <- was our has_tool_calls
builder.add_edge("tools", "chatbot")

graph = builder.compile()

result = graph.invoke(
    {"messages": [HumanMessage("What is 123456 times 654321, and what time is it?")]}
)
for m in result["messages"]:
    extra = f"  tool_calls={m.tool_calls}" if getattr(m, "tool_calls", None) else ""
    print(f"  {type(m).__name__:13} {str(m.content)[:100]!r}{extra}")

print(
    f"\n{len(result['messages'])} total messages - "
    "same shape as our hand-written loop produced in step 2."
)
