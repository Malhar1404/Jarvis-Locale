"""The shared state every node in the graph reads and updates.

`messages` is the same conversation list from Phase 1. `add_messages` is a *reducer*: when a
node returns {"messages": [new_message]}, LangGraph appends it instead of replacing the list.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # Names of ask_once tools already approved this conversation. No reducer: the tools node
    # always returns the full updated set ("last write wins", like any plain state field).
    approved_once: set[str]
