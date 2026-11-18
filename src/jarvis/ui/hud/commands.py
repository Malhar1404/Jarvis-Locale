"""Local voice/typed commands the HUD handles itself, without asking the agent.

"Interactive mode on" is a UI switch, not a PC task, so it never goes to the LLM: matching a
phrase is instant, always right, and keeps the agent from needing to know the UI exists.
A plain question that only *mentions* it ("what is interactive mode?") has no on/off verb, so
it returns None and goes to the agent as normal.
"""

import re

_MODE = re.compile(r"\b(interactive|gesture)\s+mode\b", re.IGNORECASE)
_OFF = re.compile(
    r"\b(off|stop|disable|deactivate|exit|leave|close|end|turn\s+off|switch\s+off)\b", re.I
)
_ON = re.compile(
    r"\b(on|start|enable|activate|enter|open|turn\s+on|switch\s+(on|to)|go\s+to)\b", re.I
)


def interactive_mode_command(text: str) -> bool | None:
    """True = turn on, False = turn off, None = not a mode command."""
    if not _MODE.search(text):
        return None
    if _OFF.search(text):
        return False
    if _ON.search(text):
        return True
    return None
