"""Read and set the system master volume. AUTO tier: instantly visible and reversible."""

import comtypes
from langchain_core.tools import tool
from pycaw.pycaw import AudioUtilities

from jarvis.safety.tiers import RiskTier, risk_tier


def _endpoint_volume():
    # LangGraph runs node/tool code on a worker thread, and COM must be initialized on
    # whichever thread actually touches it - safe to call every time (a no-op if already done).
    comtypes.CoInitialize()
    # This pycaw version exposes the low-level COM interface directly as a property -
    # no need for the older Activate()/cast() dance.
    return AudioUtilities.GetSpeakers().EndpointVolume


@risk_tier(RiskTier.AUTO)
@tool
def get_volume() -> int:
    """Get the current system volume as a percentage (0-100)."""
    return round(_endpoint_volume().GetMasterVolumeLevelScalar() * 100)


@risk_tier(RiskTier.AUTO)
@tool
def set_volume(level: int) -> str:
    """Set the system volume to a percentage (0-100)."""
    if not 0 <= level <= 100:
        raise ValueError(f"level must be between 0 and 100, got {level}")
    _endpoint_volume().SetMasterVolumeLevelScalar(level / 100, None)
    return f"Volume set to {level}%."
