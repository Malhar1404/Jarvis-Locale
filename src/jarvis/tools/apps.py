"""Open a known Windows application. Phase 5's first real tool - replaces Phase 4's fake stub."""

import subprocess

from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier

# A fixed, known list on purpose: launching an arbitrary program by name is close to running
# arbitrary code. Only names we recognize can be opened - anything else is a clear error,
# not a guess.
KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
}


@risk_tier(RiskTier.ASK_ONCE)
@tool
def open_app(name: str) -> str:
    """Open a known Windows application by short name: notepad, calculator, paint, or explorer."""
    exe = KNOWN_APPS.get(name.strip().lower())
    if exe is None:
        known = ", ".join(KNOWN_APPS)
        return f"Unknown app '{name}'. Known apps: {known}."
    subprocess.Popen([exe])  # exe is always one of our own fixed, known names - never user input
    return f"Opened {name}."
