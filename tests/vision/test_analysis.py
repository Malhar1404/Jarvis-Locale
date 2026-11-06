from types import SimpleNamespace

import pytest

from jarvis.vision import analysis


def test_analyze_screenshot_sends_question_and_embedded_image(monkeypatch, tmp_path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"not-a-real-png")
    seen_messages = []

    class FakeVisionModel:
        def invoke(self, messages):
            seen_messages.extend(messages)
            return SimpleNamespace(content="Application/window\nExample")

    monkeypatch.setattr(analysis, "make_vision_llm", FakeVisionModel)

    result = analysis.analyze_screenshot(screenshot, "What is open?")

    assert result == "Application/window\nExample"
    blocks = seen_messages[0].content
    assert blocks[0]["type"] == "text"
    assert "What is open?" in blocks[0]["text"]
    assert blocks[1]["image_url"].startswith("data:image/png;base64,")


def test_analyze_screenshot_rejects_missing_file(tmp_path):
    with pytest.raises(analysis.ScreenAnalysisError, match="does not exist"):
        analysis.analyze_screenshot(tmp_path / "missing.png")


def test_analyze_screenshot_wraps_model_error(monkeypatch, tmp_path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"image")

    class FailingVisionModel:
        def invoke(self, messages):
            raise TimeoutError("Ollama took too long")

    monkeypatch.setattr(analysis, "make_vision_llm", FailingVisionModel)

    with pytest.raises(analysis.ScreenAnalysisError, match="TimeoutError"):
        analysis.analyze_screenshot(screenshot)
