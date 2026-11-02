"""Run a tool call requested by the model, and never crash while doing it."""

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool


def run_tool(call: dict, tools_by_name: dict[str, BaseTool]) -> ToolMessage:
    """Run one tool call from `AIMessage.tool_calls` and return the ToolMessage to send back.

    Any problem (unknown tool, bad arguments, an exception inside the tool) becomes an error
    message for the model instead of a crash, so the model can explain it or try again.
    """
    name, call_id = call["name"], call["id"]

    tool = tools_by_name.get(name)
    if tool is None:
        known = ", ".join(tools_by_name)
        text = f"Error: there is no tool called '{name}'. Available tools: {known}."
        return ToolMessage(content=text, tool_call_id=call_id, status="error")

    try:
        result = tool.invoke(call["args"])
    except Exception as exc:  # noqa: BLE001  (we want to catch everything a tool can raise)
        text = f"Error while running {name}: {type(exc).__name__}: {exc}"
        return ToolMessage(content=text, tool_call_id=call_id, status="error")

    return ToolMessage(content=str(result), tool_call_id=call_id)
