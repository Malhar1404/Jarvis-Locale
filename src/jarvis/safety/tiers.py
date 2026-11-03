"""Risk tiers: every tool must declare how much it is trusted to run on its own.

See CLAUDE.md: "Permissions are enforced in Python (safety/), never only in the prompt."
This file only defines what a tier means - nothing here talks to an LLM or a graph.
"""

from enum import StrEnum

from langchain_core.tools import BaseTool


class RiskTier(StrEnum):
    """How much a tool is trusted to run without asking the user first."""

    AUTO = "auto"  # runs immediately, no question asked (e.g. read the clock)
    ASK_ONCE = "ask_once"  # ask the first time per tool in a conversation, then remember "yes"
    ALWAYS_ASK = "always_ask"  # ask every single time, no matter what
    NEVER = "never"  # the agent must never run this tool at all


def risk_tier(tier: RiskTier):
    """Decorator: stack directly above @tool to declare its risk tier.

    @risk_tier(RiskTier.AUTO)
    @tool
    def get_time() -> str: ...
    """

    def decorator(t: BaseTool) -> BaseTool:
        t.metadata = {**(t.metadata or {}), "risk_tier": tier.value}
        return t

    return decorator


def get_risk_tier(t: BaseTool) -> RiskTier:
    """Read a tool's declared tier. Undeclared tools default to ALWAYS_ASK - fail safe, not open."""
    value = (t.metadata or {}).get("risk_tier")
    return RiskTier(value) if value else RiskTier.ALWAYS_ASK
