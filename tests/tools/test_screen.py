import json

from jarvis.tools import screen
from jarvis.vision.screen_capture import ScreenCapture


def test_inspect_screen_always_uses_the_full_desktop(monkeypatch, tmp_path):
    captures = [
        ScreenCapture(
            mode="full_desktop",
            path=tmp_path / "monitor-1.png",
            width=1920,
            height=1080,
            left=0,
            top=0,
            monitor_count=2,
            monitor_index=1,
        ),
        ScreenCapture(
            mode="full_desktop",
            path=tmp_path / "monitor-2.png",
            width=1920,
            height=1080,
            left=-1920,
            top=0,
            monitor_count=2,
            monitor_index=2,
        ),
    ]
    monkeypatch.setattr(screen, "capture_each_monitor", lambda: captures)
    monkeypatch.setattr(screen, "analyze_screenshot", lambda path, question: f"Saw {path.stem}.")

    result = json.loads(screen.inspect_screen.invoke({"question": "What is open?"}))

    assert result["mode"] == "full_desktop"
    assert result["monitor_count"] == 2
    assert result["image_size"] == [3840, 1080]
    assert [monitor["visual_analysis"] for monitor in result["monitors"]] == [
        "Saw monitor-1.",
        "Saw monitor-2.",
    ]


def test_inspect_screen_exposes_no_active_window_mode():
    properties = screen.inspect_screen.args_schema.model_json_schema()["properties"]

    assert set(properties) == {"question"}
