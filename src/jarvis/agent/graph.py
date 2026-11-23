"""The real agent loop: chatbot <-> tools, looping until the model stops asking for tools.

This is the Phase 1 round trip (ask -> run tool -> ask again) redrawn as a graph, so it can
repeat as many times as a task needs instead of running exactly once.
"""

from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, trim_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from jarvis.agent.state import AgentState
from jarvis.config import HISTORY_TRIM_TOKENS
from jarvis.llm import make_llm
from jarvis.safety.approval import run_tool_calls_with_approval

_SCREEN_WORDS = ("screen", "desktop", "monitor", "monitors")


def screen_question(message: BaseMessage) -> str | None:
    """Recognize unambiguous screen-inspection requests without asking a small model to plan."""
    if not isinstance(message, HumanMessage) or not isinstance(message.content, str):
        return None
    text = message.content.strip()
    return text if any(word in text.lower() for word in _SCREEN_WORDS) else None


def has_tool_calls(message: BaseMessage) -> bool:
    """Human messages have no tool_calls attribute; only AI messages may request tools."""
    return bool(getattr(message, "tool_calls", []))


def trim_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Bound what gets sent to the model this turn - the full history still lives in the
    checkpoint (so the UI and restarts are unaffected), this only trims the model's *input*.
    No-op for a conversation still under the budget. start_on="human" avoids ever starting the
    trimmed window on a lone ToolMessage, which some providers reject without its matching
    AIMessage tool call right before it.
    """
    return trim_messages(
        messages,
        max_tokens=HISTORY_TRIM_TOKENS,
        token_counter="approximate",
        strategy="last",
        include_system=True,
        start_on="human",
    )


def build_graph(tools: list[BaseTool], checkpointer: BaseCheckpointSaver | None = None):
    """Build and compile the agent graph for a given set of tools.

    A checkpointer is only required if any tool's risk tier can call interrupt() - see
    jarvis.safety.approval. Examples with only `auto` tools can omit it.
    """
    tools_by_name = {t.name: t for t in tools}
    llm = make_llm().bind_tools(tools)

    def chatbot(state: AgentState) -> dict:
        reply = llm.invoke(trim_history(state["messages"]))
        return {"messages": [reply]}

    def route_screen_intent(state: AgentState) -> dict:
        """Make direct screen/desktop requests reliable while leaving all other requests agentic."""
        question = screen_question(state["messages"][-1])
        if question is None or "inspect_screen" not in tools_by_name:
            return {}
        call = {
            "name": "inspect_screen",
            "args": {"question": question},
            "id": f"screen-{uuid4().hex}",
            "type": "tool_call",
        }
        return {"messages": [AIMessage(content="", tool_calls=[call])]}

    def run_tools(state: AgentState) -> dict:
        last: BaseMessage = state["messages"][-1]
        approved = set(state.get("approved_once", set()))
        results, approved = run_tool_calls_with_approval(last.tool_calls, tools_by_name, approved)
        return {"messages": results, "approved_once": approved}

    def route_after_chatbot(state: AgentState) -> str:
        """The conditional edge: decide where to go after `chatbot` runs."""
        last: BaseMessage = state["messages"][-1]
        return "tools" if has_tool_calls(last) else "end"

    def after_screen_router(state: AgentState) -> str:
        last: BaseMessage = state["messages"][-1]
        return "tools" if has_tool_calls(last) else "chatbot"

    builder = StateGraph(AgentState)
    builder.add_node("screen_intent", route_screen_intent)
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", run_tools)

    builder.add_edge(START, "screen_intent")
    builder.add_conditional_edges(
        "screen_intent", after_screen_router, {"tools": "tools", "chatbot": "chatbot"}
    )
    builder.add_conditional_edges("chatbot", route_after_chatbot, {"tools": "tools", "end": END})
    builder.add_edge("tools", "chatbot")  # always loop back so the model sees the result

    return builder.compile(checkpointer=checkpointer)
