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


class ApprovalRequest(BaseModel):
    """A tool call is paused (see jarvis.safety.approval) - the graph will not continue until
    something calls Agent.resume("yes"/"no") with the user's decision.
    """

    type: Literal["approval_request"] = "approval_request"
    name: str
    args: dict
    tier: str


class ScreenShot(BaseModel):
    path: str  # local PNG under .data/screen_captures - only UIs read it, never the text model
    label: str  # e.g. "Monitor 1 · 2560×1440"


class ScreenCaptured(BaseModel):
    """inspect_screen took its screenshots. Sent mid-tool through LangGraph's *custom* stream
    (see tools/screen.py), so a UI can show the images before the vision model has finished.
    """

    type: Literal["screen_captured"] = "screen_captured"
    shots: list[ScreenShot]


class VisionResult(BaseModel):
    """The vision model finished describing one screenshot."""

    type: Literal["vision_result"] = "vision_result"
    label: str
    text: str
    seconds: float


AgentEvent = (
    Thinking
    | Token
    | ToolCall
    | ToolResult
    | Error
    | ApprovalRequest
    | ScreenCaptured
    | VisionResult
)
