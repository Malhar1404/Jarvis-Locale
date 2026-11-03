"""The approval gate: decides whether a requested tool call may run, asking the user via
interrupt() when its risk tier demands it. CLAUDE.md: "Permissions are enforced in Python
(safety/), never only in the prompt" - this is that enforcement point.
"""

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.types import interrupt

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.runner import run_tool


def run_tool_with_approval(
    call: dict, tools_by_name: dict[str, BaseTool], approved_once: set[str]
) -> tuple[ToolMessage, set[str]]:
    """Run one tool call, pausing for approval first if its tier requires it.

    Returns the ToolMessage to send back to the model, and the (possibly updated) set of
    ask_once tools approved so far this conversation.
    """
    name = call["name"]
    tool = tools_by_name.get(name)
    tier = get_risk_tier(tool) if tool else RiskTier.ALWAYS_ASK

    if tier is RiskTier.NEVER:
        text = f"Denied: '{name}' is risk tier 'never' and can never run."
        msg = ToolMessage(content=text, tool_call_id=call["id"], name=name, status="error")
        return msg, approved_once

    is_new_ask_once = tier is RiskTier.ASK_ONCE and name not in approved_once
    needs_ask = tier is RiskTier.ALWAYS_ASK or is_new_ask_once
    if needs_ask:
        decision = interrupt({"name": name, "args": call["args"], "tier": tier.value})
        if decision != "yes":
            text = f"The user denied running '{name}'."
            return ToolMessage(
                content=text, tool_call_id=call["id"], name=name, status="error"
            ), approved_once
        if tier is RiskTier.ASK_ONCE:
            approved_once = approved_once | {name}

    return run_tool(call, tools_by_name), approved_once
