"""The approval gate: decides whether requested tool calls may run, asking the user via
interrupt() when their risk tier demands it. CLAUDE.md: "Permissions are enforced in Python
(safety/), never only in the prompt" - this is that enforcement point.

IMPORTANT ordering rule: a node that calls interrupt() reruns from the top on resume (see
docs/phases/phase-04-safety.md). If call A ran before call B paused the node, A would run AGAIN
on replay - a real duplicate action, not just a duplicate print. So we resolve every approval
first (decide() only ever calls interrupt(), never run_tool()), and only run tools in a second
pass that starts once nothing can pause anymore.
"""

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.types import interrupt

from jarvis.safety.audit import log_tool_call
from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.runner import run_tool


def decide(
    call: dict, tools_by_name: dict[str, BaseTool], approved_once: set[str]
) -> tuple[bool, ToolMessage | None, str, str, set[str]]:
    """Resolve whether one call may run. The only place interrupt() is called - never runs
    the tool itself, so it is always safe to replay.

    Returns (allowed, denial_message_or_None, tier, decision_label, updated approved_once).
    decision_label is one of "auto" / "approved" / "denied" / "blocked" - for the audit log.
    """
    name = call["name"]
    tool = tools_by_name.get(name)
    tier = get_risk_tier(tool) if tool else RiskTier.ALWAYS_ASK

    if tier is RiskTier.NEVER:
        text = f"Denied: '{name}' is risk tier 'never' and can never run."
        msg = ToolMessage(content=text, tool_call_id=call["id"], name=name, status="error")
        return False, msg, tier.value, "blocked", approved_once

    is_new_ask_once = tier is RiskTier.ASK_ONCE and name not in approved_once
    needs_ask = tier is RiskTier.ALWAYS_ASK or is_new_ask_once
    if needs_ask:
        response = interrupt({"name": name, "args": call["args"], "tier": tier.value})
        if response != "yes":
            text = f"The user denied running '{name}'."
            msg = ToolMessage(content=text, tool_call_id=call["id"], name=name, status="error")
            return False, msg, tier.value, "denied", approved_once
        if tier is RiskTier.ASK_ONCE:
            approved_once = approved_once | {name}
        return True, None, tier.value, "approved", approved_once

    return True, None, tier.value, "auto", approved_once


def run_tool_calls_with_approval(
    calls: list[dict], tools_by_name: dict[str, BaseTool], approved_once: set[str]
) -> tuple[list[ToolMessage], set[str]]:
    """Run a whole batch of tool calls, resolving ALL approvals before running ANY tool."""
    decisions = []
    for call in calls:
        allowed, denial, tier, decision, approved_once = decide(call, tools_by_name, approved_once)
        decisions.append((call, allowed, denial, tier, decision))

    results = []
    for call, allowed, denial, tier, decision in decisions:
        result = denial if not allowed else run_tool(call, tools_by_name)
        log_tool_call(
            name=call["name"],
            args=call["args"],
            tier=tier,
            decision=decision,
            status="error" if result.status == "error" else "ok",
        )
        results.append(result)
    return results, approved_once
