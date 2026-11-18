from jarvis.agent.events import ScreenCaptured, VisionResult
from jarvis.agent.runner import _custom_event


def test_screen_captured_report_becomes_an_event():
    event = _custom_event(
        {"type": "screen_captured", "shots": [{"path": "a.png", "label": "Monitor 1"}]}
    )
    assert isinstance(event, ScreenCaptured)
    assert event.shots[0].path == "a.png"


def test_vision_report_becomes_an_event():
    event = _custom_event({"type": "vision_result", "label": "M1", "text": "hi", "seconds": 1.5})
    assert isinstance(event, VisionResult)


def test_unknown_or_broken_reports_are_dropped():
    assert _custom_event({"type": "something_else"}) is None
    assert _custom_event({"type": "vision_result"}) is None  # missing fields
    assert _custom_event("not a dict") is None
