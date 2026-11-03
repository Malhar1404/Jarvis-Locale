"""Small, harmless tools used to learn tool calling (Phase 1)."""

import shutil
from datetime import datetime
from pathlib import Path

import psutil
from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.AUTO)
@tool
def get_time() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%A, %d %B %Y, %H:%M")


@risk_tier(RiskTier.AUTO)
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two whole numbers and return the result."""
    return a * b


@risk_tier(RiskTier.AUTO)
@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second number and return the result."""
    return a / b  # raises ZeroDivisionError when b is 0, on purpose: we test error handling


@risk_tier(RiskTier.AUTO)
@tool
def get_system_info() -> str:
    """Get this PC's current CPU usage, memory usage, disk space and battery level."""
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.home().anchor)
    battery = psutil.sensors_battery()  # None on PCs without a battery
    battery_text = (
        f"{battery.percent:.0f}% ({'charging' if battery.power_plugged else 'on battery'})"
        if battery
        else "no battery found"
    )
    return (
        f"CPU: {psutil.cpu_percent(interval=0.5):.0f}% used\n"
        f"Memory: {memory.percent:.0f}% used of {memory.total / 1e9:.1f} GB\n"
        f"Disk ({Path.home().anchor}): {disk.free / 1e9:.0f} GB free of {disk.total / 1e9:.0f} GB\n"
        f"Battery: {battery_text}"
    )
