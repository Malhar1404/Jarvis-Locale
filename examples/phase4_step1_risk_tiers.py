"""Phase 4, step 1: risk tiers - pure data, no approval flow yet.

Run with:  uv run python examples/phase4_step1_risk_tiers.py
"""

from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.basic import divide, get_system_info, get_time, multiply


@tool
def undeclared_tool() -> str:
    """A tool that forgot to declare @risk_tier - on purpose, for this demo."""
    return "oops"


print("Declared tools:")
for t in [get_time, multiply, divide, get_system_info]:
    print(f"  {t.name:16} -> {get_risk_tier(t).value}")

print("\nAn undeclared tool (no @risk_tier at all):")
tier = get_risk_tier(undeclared_tool)
print(f"  {undeclared_tool.name:16} -> {tier.value}")
assert tier == RiskTier.ALWAYS_ASK, "fail-safe default broke!"
print("\nFail-safe default confirmed: forgetting to declare a tier means 'always ask', not 'auto'.")
