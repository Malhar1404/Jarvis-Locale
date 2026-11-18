"""Read-only Screen Awareness tool used by the LangGraph agent."""

import time

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from jarvis.safety.tiers import RiskTier, risk_tier
from jarvis.vision.analysis import DEFAULT_SCREEN_QUESTION, analyze_screenshot
from jarvis.vision.context import ScreenInspection
from jarvis.vision.screen_capture import capture_each_monitor


def _report(payload: dict) -> None:
    """Send a progress report to whoever is streaming the graph (the HUD's Mind panel).

    get_stream_writer() only works while running inside a graph. Called anywhere else nobody is
    listening, so there is nothing to do. Outside any runnable it raises RuntimeError; inside a
    plain tool.invoke() (a LangChain config, but no LangGraph runtime) it raises KeyError.
    """
    try:
        writer = get_stream_writer()
    except (RuntimeError, KeyError):
        return
    writer(payload)


@risk_tier(RiskTier.ASK_ONCE)
@tool
def inspect_screen(question: str = DEFAULT_SCREEN_QUESTION) -> str:
    """Capture and analyze the user's screen for questions about visible apps, UI, or errors.

    Always capture every connected monitor and analyze each internally before returning one
    combined desktop result. This captures a fresh snapshot only when called; it never monitors
    the screen in the background.
    """
    captures = capture_each_monitor()
    _report(
        {
            "type": "screen_captured",
            "shots": [
                {
                    "path": str(capture.path),
                    "label": f"Monitor {capture.monitor_index} · {capture.width}×{capture.height}",
                }
                for capture in captures
            ],
        }
    )
    analyses = []
    for capture in captures:
        started = time.monotonic()
        analysis = analyze_screenshot(
            capture.path,
            f"Monitor {capture.monitor_index} of {capture.monitor_count}. {question}",
        )
        analyses.append(analysis)
        _report(
            {
                "type": "vision_result",
                "label": f"Monitor {capture.monitor_index}",
                "text": analysis,
                "seconds": round(time.monotonic() - started, 1),
            }
        )
    context = ScreenInspection.from_monitor_captures(captures, question=question, analyses=analyses)
    return context.model_dump_json(exclude_defaults=True)
