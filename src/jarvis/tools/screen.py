"""Read-only Screen Awareness tool used by the LangGraph agent."""

from typing import Literal

from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier
from jarvis.vision.analysis import DEFAULT_SCREEN_QUESTION, analyze_screenshot
from jarvis.vision.context import ScreenInspection
from jarvis.vision.screen_capture import capture_active_window, capture_full_desktop

ScreenMode = Literal["active_window", "full_desktop"]


@risk_tier(RiskTier.ASK_ONCE)
@tool
def inspect_screen(
    question: str = DEFAULT_SCREEN_QUESTION, mode: ScreenMode = "active_window"
) -> str:
    """Capture and analyze the user's screen for questions about visible apps, UI, or errors.

    Use active_window for the currently focused app (the default), and full_desktop only when the
    user explicitly asks about every monitor or their whole desktop. This captures a fresh image
    only when called; it never monitors the screen in the background.
    """
    capture = capture_active_window() if mode == "active_window" else capture_full_desktop()
    visual_analysis = analyze_screenshot(capture.path, question)
    context = ScreenInspection.from_capture(
        capture,
        question=question,
        visual_analysis=visual_analysis,
    )
    return context.model_dump_json()
