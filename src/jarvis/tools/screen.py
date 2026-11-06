"""Read-only Screen Awareness tool used by the LangGraph agent."""

from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier
from jarvis.vision.analysis import DEFAULT_SCREEN_QUESTION, analyze_screenshot
from jarvis.vision.context import ScreenInspection
from jarvis.vision.screen_capture import capture_each_monitor


@risk_tier(RiskTier.ASK_ONCE)
@tool
def inspect_screen(question: str = DEFAULT_SCREEN_QUESTION) -> str:
    """Capture and analyze the user's screen for questions about visible apps, UI, or errors.

    Always capture every connected monitor and analyze each internally before returning one
    combined desktop result. This captures a fresh snapshot only when called; it never monitors
    the screen in the background.
    """
    captures = capture_each_monitor()
    analyses = [
        analyze_screenshot(
            capture.path,
            f"Monitor {capture.monitor_index} of {capture.monitor_count}. {question}",
        )
        for capture in captures
    ]
    context = ScreenInspection.from_monitor_captures(
        captures, question=question, analyses=analyses
    )
    return context.model_dump_json(exclude_defaults=True)
