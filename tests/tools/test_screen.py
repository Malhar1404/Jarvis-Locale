import json

from jarvis.tools import screen
from jarvis.vision.screen_capture import ScreenCapture, WindowInfo


def test_inspect_screen_hands_structured_vision_context_to_agent(monkeypatch, tmp_path):
    capture = ScreenCapture(
        mode="active_window",
        path=tmp_path / "private-image.png",
        width=800,
        height=600,
        left=20,
        top=10,
        monitor_count=2,
        window=WindowInfo(handle=1, title="Calculator", left=20, top=10, width=800, height=600),
    )
    monkeypatch.setattr(screen, "capture_active_window", lambda: capture)
    monkeypatch.setattr(
        screen, "analyze_screenshot", lambda path, question: "A calculator is open."
    )

    result = json.loads(
        screen.inspect_screen.invoke({"question": "What app am I using?", "mode": "active_window"})
    )

    assert result == {
        "mode": "active_window",
        "question": "What app am I using?",
        "image_size": [800, 600],
        "screen_position": [20, 10],
        "monitor_count": 2,
        "active_window_title": "Calculator",
        "visual_analysis": "A calculator is open.",
    }


def test_inspect_screen_uses_full_desktop_only_when_requested(monkeypatch, tmp_path):
    capture = ScreenCapture(
        mode="full_desktop",
        path=tmp_path / "image.png",
        width=3840,
        height=1080,
        left=0,
        top=0,
        monitor_count=2,
    )
    monkeypatch.setattr(screen, "capture_full_desktop", lambda: capture)
    monkeypatch.setattr(
        screen, "analyze_screenshot", lambda path, question: "Two monitors are visible."
    )

    result = json.loads(screen.inspect_screen.invoke({"mode": "full_desktop"}))

    assert result["mode"] == "full_desktop"
    assert result["visual_analysis"] == "Two monitors are visible."
