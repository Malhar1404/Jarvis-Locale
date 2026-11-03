"""The real agent loop: chatbot <-> tools, looping until the model stops asking for tools.

This is the Phase 1 round trip (ask -> run tool -> ask again) redrawn as a graph, so it can
repeat as many times as a task needs instead of running exactly once.
"""

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from jarvis.agent.state import AgentState
from jarvis.llm import make_llm
from jarvis.tools.runner import run_tool


def build_graph(tools: list[BaseTool]):
    """Build and compile the agent graph for a given set of tools."""
    tools_by_name = {t.name: t for t in tools}
    llm = make_llm().bind_tools(tools)

    def chatbot(state: AgentState) -> dict:
        reply = llm.invoke(state["messages"])
        return {"messages": [reply]}

    def run_tools(state: AgentState) -> dict:
        last: BaseMessage = state["messages"][-1]
        results = [run_tool(call, tools_by_name) for call in last.tool_calls]
        return {"messages": results}

    def has_tool_calls(state: AgentState) -> str:
        """The conditional edge: decide where to go after `chatbot` runs."""
        last: BaseMessage = state["messages"][-1]
        return "tools" if last.tool_calls else "end"

    builder = StateGraph(AgentState)
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", run_tools)

    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges("chatbot", has_tool_calls, {"tools": "tools", "end": END})
    builder.add_edge("tools", "chatbot")  # always loop back so the model sees the result

    return builder.compile()
