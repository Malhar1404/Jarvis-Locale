"""The agent's public API. A UI calls `Agent.run(text)` / `Agent.resume(decision)` and gets back
`AgentEvent`s - it never touches LangGraph's stream, nodes, checkpointer, or message types.
"""

import sqlite3
from collections.abc import Iterator

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import ValidationError

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    ScreenCaptured,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
    VisionResult,
)
from jarvis.agent.graph import build_graph
from jarvis.config import CHECKPOINT_DB_PATH, HISTORY_TRIM_TOKENS, THREAD_ID
from jarvis.llm import make_llm

# Below this many old messages, compacting isn't worth an extra LLM call - trim_history() in
# graph.py already keeps ordinary turns within budget on its own.
_COMPACT_MIN_OLD_MESSAGES = 6


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
        if existing:
            # Checkpoints intentionally preserve a conversation across restarts, but the system
            # prompt is application configuration, not conversation content.  Keep the original
            # message id so add_messages replaces it in place rather than appending a conflicting
            # second system instruction halfway through the history.
            messages = _with_current_system_prompt(list(existing["messages"]), system_prompt)
            self._graph.update_state(self._config, {"messages": messages})
            self.history = list(self._graph.get_state(self._config).values["messages"])
        else:
            self.history = [SystemMessage(system_prompt)]

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

    def context_usage(self) -> tuple[int, int]:
        """(approximate tokens in the full stored history, the per-turn send budget). The first
        number can exceed the second - that just means trim_history() is already quietly
        dropping old messages each turn; compact() turns that into a kept summary instead.
        """
        return count_tokens_approximately(self.history), HISTORY_TRIM_TOKENS

    def compact(self) -> str:
        """Summarize the oldest part of the conversation with one LLM call, replacing those
        messages in the checkpoint with a short summary - keeps their gist instead of letting
        trim_history() silently drop them from what the model ever sees again.
        """
        old = _old_messages(self.history)
        if len(old) < _COMPACT_MIN_OLD_MESSAGES:
            return "Nothing to compact yet."

        transcript = "\n".join(line for m in old if (line := _transcript_line(m)))
        summary = (
            make_llm()
            .invoke(
                [
                    SystemMessage(
                        "Summarize the following conversation in 3-6 plain sentences. Preserve "
                        "names, facts, and anything the user asked to be remembered. No markdown."
                    ),
                    HumanMessage(transcript),
                ]
            )
            .content
        )

        summary_message = SystemMessage(
            f"Summary of {len(old)} earlier messages (background context): {summary}"
        )
        removals = [RemoveMessage(id=message.id) for message in old]
        self._graph.update_state(self._config, {"messages": [*removals, summary_message]})
        self.history = list(self._graph.get_state(self._config).values["messages"])
        return f"Compacted {len(old)} older messages into a summary."

    def _drive(self, graph_input: dict | Command) -> Iterator[AgentEvent]:
        announced_nodes: set[str] = set()
        try:
            stream = self._graph.stream(
                graph_input, config=self._config, stream_mode=["updates", "messages", "custom"]
            )
            for mode, payload in stream:
                if mode == "custom":  # progress a tool reported mid-run via get_stream_writer()
                    event = _custom_event(payload)
                    if event is not None:
                        yield event
                elif mode == "messages":
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
                        # LangGraph reports a node that returned {} (no change, e.g. screen_intent
                        # on a non-screen message) as None here, not {} - checked directly.
                        if not change:
                            continue
                        for msg in change["messages"]:
                            self.history.append(msg)
                            yield from _events_for(node_name, msg)
        except Exception as exc:  # noqa: BLE001  (the graph/model call itself failed, not a tool)
            yield Error(message=f"{type(exc).__name__}: {exc}")


_CUSTOM_EVENTS = {"screen_captured": ScreenCaptured, "vision_result": VisionResult}


def _custom_event(payload: object) -> AgentEvent | None:
    """Turn a tool's plain-dict progress report into a typed event. Tools send dicts (not our
    event classes) so jarvis.tools never has to import jarvis.agent. Unknown or malformed
    reports are dropped - progress display must never break a turn.
    """
    if not isinstance(payload, dict):
        return None
    event_class = _CUSTOM_EVENTS.get(payload.get("type"))
    if event_class is None:
        return None
    try:
        return event_class.model_validate(payload)
    except ValidationError:
        return None


def _events_for(node_name: str, msg: BaseMessage) -> Iterator[AgentEvent]:
    # screen_intent can also request a tool (a direct "look at my screen" skips the model).
    if node_name in ("chatbot", "screen_intent") and isinstance(msg, AIMessage) and msg.tool_calls:
        for call in msg.tool_calls:
            yield ToolCall(name=call["name"], args=call["args"])
    elif node_name == "tools" and isinstance(msg, ToolMessage):
        status = "error" if msg.status == "error" else "ok"
        yield ToolResult(name=msg.name or "unknown", content=str(msg.content), status=status)


def _old_messages(history: list[BaseMessage]) -> list[BaseMessage]:
    """Which messages are old enough to compact away - the same recent window trim_history()
    (see graph.py) would already keep, so compacting never discards something still in budget.
    """
    kept = trim_messages(
        history,
        max_tokens=HISTORY_TRIM_TOKENS // 2,
        token_counter="approximate",
        strategy="last",
        include_system=True,
        start_on="human",
    )
    kept_ids = {message.id for message in kept}
    return [message for message in history if message.id not in kept_ids]


def _transcript_line(message: BaseMessage) -> str:
    """One readable line for the summarization prompt - tool calls/results add noise there, not
    substance, so only the human/assistant turns with actual text are included.
    """
    if isinstance(message, HumanMessage) and isinstance(message.content, str):
        return f"User: {message.content}"
    if isinstance(message, AIMessage) and isinstance(message.content, str) and message.content:
        return f"Jarvis: {message.content}"
    return ""


def _with_current_system_prompt(
    messages: list[BaseMessage], system_prompt: str
) -> list[BaseMessage]:
    """Replace the persisted system message while retaining every user/assistant turn."""
    for index, message in enumerate(messages):
        if isinstance(message, SystemMessage):
            updated = SystemMessage(content=system_prompt, id=message.id)
            return [*messages[:index], updated, *messages[index + 1 :]]
    return [SystemMessage(system_prompt), *messages]
