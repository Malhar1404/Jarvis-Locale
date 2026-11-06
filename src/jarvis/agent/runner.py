"""The agent's public API. A UI calls `Agent.run(text)` / `Agent.resume(decision)` and gets back
`AgentEvent`s - it never touches LangGraph's stream, nodes, checkpointer, or message types.
"""

import sqlite3
from collections.abc import Iterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
)
from jarvis.agent.graph import build_graph
from jarvis.config import CHECKPOINT_DB_PATH, THREAD_ID


class Agent:
    """Owns one compiled graph plus the growing message history for one conversation.

    The checkpointer writes to a SQLite file instead of RAM, and reuses the same thread_id every
    run, so the conversation (and any paused approval) survives restarting the app - not just a
    rerun within the same process.
    """

    def __init__(self, tools: list[BaseTool], system_prompt: str) -> None:
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the UI opens this connection on the main thread, but the
        # graph actually runs on the worker QThread (see ui/worker.py) - the same kind of
        # cross-thread rule pycaw taught us in Phase 5, this time for sqlite3 instead of COM.
        conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
        self._graph = build_graph(tools, checkpointer=SqliteSaver(conn))
        self._config = {"configurable": {"thread_id": THREAD_ID}}

        # Resume from whatever the checkpoint already has (a real restart), instead of always
        # starting from just the system prompt. `_seeded` tracks whether the graph's own stored
        # state already has *anything* in it - if so, every future run() must send only the new
        # message(s), never the full history again, or the system prompt gets duplicated into
        # the middle of the conversation on every restart (checked with a throwaway script before
        # writing this - the reducer appends by message id, and a freshly-built SystemMessage
        # gets a new id every time, so it looks "new" to it).
        existing = self._graph.get_state(self._config).values
        self._seeded = bool(existing)
        self.history: list[BaseMessage] = (
            list(existing["messages"]) if existing else [SystemMessage(system_prompt)]
        )

    def run(self, text: str) -> Iterator[AgentEvent]:
        """Send one new user message through the graph, yielding events as they happen.

        May stop at an ApprovalRequest - the graph is then paused; call resume() to continue it.
        """
        new_message = HumanMessage(text)
        # First run ever for this thread_id: the graph has never seen the system prompt, so it
        # has to go in as input too. Every run after that, the checkpoint already holds
        # everything up to this point - send only what's new.
        graph_input = self.history + [new_message] if not self._seeded else [new_message]
        self._seeded = True
        self.history.append(new_message)
        yield from self._drive({"messages": graph_input})

    def resume(self, decision: str) -> Iterator[AgentEvent]:
        """Continue a graph paused on an ApprovalRequest. decision is "yes" or "no"."""
        yield from self._drive(Command(resume=decision))

    def _drive(self, graph_input: dict | Command) -> Iterator[AgentEvent]:
        announced_nodes: set[str] = set()
        try:
            stream = self._graph.stream(
                graph_input, config=self._config, stream_mode=["updates", "messages"]
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
                elif "__interrupt__" in payload:
                    data = payload["__interrupt__"][0].value
                    yield ApprovalRequest(**data)
                    return  # graph is paused - stop until resume() is called
                else:  # a node just finished - grow history, emit its events
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
