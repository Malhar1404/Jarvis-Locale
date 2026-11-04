"""Read and set the screen brightness. AUTO tier: instantly visible and reversible."""

import screen_brightness_control as sbc
from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.AUTO)
@tool
def get_brightness() -> int:
    """Get the current screen brightness as a percentage (0-100)."""
    return sbc.get_brightness()[0]  # one value per monitor; report the first/primary one


@risk_tier(RiskTier.AUTO)
@tool
def set_brightness(level: int) -> str:
    """Set the screen brightness to a percentage (0-100), on every connected monitor."""
    if not 0 <= level <= 100:
        raise ValueError(f"level must be between 0 and 100, got {level}")
    sbc.set_brightness(level)
    return f"Brightness set to {level}%."
