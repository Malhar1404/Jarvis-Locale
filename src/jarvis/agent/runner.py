"""The agent's public API. A UI calls `Agent.run(text)` and gets back `AgentEvent`s - it never
touches LangGraph's stream, nodes, or message types directly.
"""

from collections.abc import Iterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from jarvis.agent.events import AgentEvent, Error, Thinking, Token, ToolCall, ToolResult
from jarvis.agent.graph import build_graph


class Agent:
    """Owns one compiled graph plus the growing message history for one conversation."""

    def __init__(self, tools: list[BaseTool], system_prompt: str) -> None:
        self._graph = build_graph(tools)
        self.history: list[BaseMessage] = [SystemMessage(system_prompt)]

    def run(self, text: str) -> Iterator[AgentEvent]:
        """Send one user message through the graph, yielding events as they happen."""
        self.history.append(HumanMessage(text))
        announced_nodes: set[str] = set()

        try:
            stream = self._graph.stream(
                {"messages": self.history}, stream_mode=["updates", "messages"]
            )
            for mode, payload in stream:
                if mode == "messages":
                    chunk, metadata = payload
                    node = metadata.get("langgraph_node")
                    if node not in announced_nodes:
                        announced_nodes.add(node)
                        yield Thinking(node=node)
                    if node == "chatbot" and chunk.content:
                        yield Token(text=chunk.content)
                else:  # mode == "updates": a node just finished - grow history, emit its events
                    for node_name, change in payload.items():
                        for msg in change["messages"]:
                            self.history.append(msg)
                            yield from _events_for(node_name, msg)
        except Exception as exc:  # noqa: BLE001  (the graph/model call itself failed, not a tool)
            yield Error(message=f"{type(exc).__name__}: {exc}")


def _events_for(node_name: str, msg: BaseMessage) -> Iterator[AgentEvent]:
    if node_name == "chatbot" and isinstance(msg, AIMessage) and msg.tool_calls:
        for call in msg.tool_calls:
            yield ToolCall(name=call["name"], args=call["args"])
    elif node_name == "tools" and isinstance(msg, ToolMessage):
        status = "error" if msg.status == "error" else "ok"
        yield ToolResult(name=msg.name or "unknown", content=str(msg.content), status=status)
