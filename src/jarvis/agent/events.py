"""The agent's public vocabulary: every UI (CLI, Qt, ...) only ever needs to know these types,
never how LangGraph's stream or state actually work.
"""

from typing import Literal

from pydantic import BaseModel


class Thinking(BaseModel):
    """The model is working (a node started running), before any text/tool-call arrives."""

    type: Literal["thinking"] = "thinking"
    node: str  # which graph node, e.g. "chatbot"


class Token(BaseModel):
    """One streamed piece of the model's final text answer."""

    type: Literal["token"] = "token"
    text: str


class ToolCall(BaseModel):
    """The model asked to run a tool (it has not run yet)."""

    type: Literal["tool_call"] = "tool_call"
    name: str
    args: dict


class ToolResult(BaseModel):
    """A tool finished running (see run_tool - errors are returned here, not raised)."""

    type: Literal["tool_result"] = "tool_result"
    name: str
    content: str
    status: Literal["ok", "error"] = "ok"


class Error(BaseModel):
    """Something went wrong in the agent runner itself, outside any tool."""

    type: Literal["error"] = "error"
    message: str


# ApprovalRequest joins this union in Phase 4, once there is something to approve.
AgentEvent = Thinking | Token | ToolCall | ToolResult | Error
