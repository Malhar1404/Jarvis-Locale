from pathlib import Path

from jarvis.vision import screen_capture
from jarvis.vision.screen_capture import WindowInfo


class FakeImage:
    rgb = b"pixels"
    size = (640, 480)
    width = 640
    height = 480


class FakeMSS:
    monitors = [
        {"left": -1920, "top": 0, "width": 3840, "height": 1080},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": -1920, "top": 0, "width": 1920, "height": 1080},
    ]

    def __init__(self) -> None:
        self.grabbed_region: dict[str, int] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def grab(self, region: dict[str, int]) -> FakeImage:
        self.grabbed_region = region
        return FakeImage()


def _set_fake_capture(monkeypatch, tmp_path: Path) -> list[dict[str, int]]:
    sessions: list[FakeMSS] = []

    def fake_mss() -> FakeMSS:
        session = FakeMSS()
        sessions.append(session)
        return session

    def fake_write_png(rgb: bytes, size: tuple[int, int], output: str) -> None:
        Path(output).write_bytes(b"fake-png")

    monkeypatch.setattr(screen_capture, "mss", fake_mss)
    monkeypatch.setattr(screen_capture.tools, "to_png", fake_write_png)
    monkeypatch.setattr(screen_capture, "enable_per_monitor_dpi_awareness", lambda: None)
    return [session.grabbed_region for session in sessions if session.grabbed_region is not None]


def test_capture_active_window_uses_foreground_bounds(monkeypatch, tmp_path):
    _set_fake_capture(monkeypatch, tmp_path)
    window = WindowInfo(handle=42, title="Example", left=-50, top=20, width=800, height=600)
    monkeypatch.setattr(screen_capture, "get_active_window", lambda: window)

    result = screen_capture.capture_active_window(tmp_path)

    assert result.mode == "active_window"
    assert result.window == window
    assert (result.left, result.top, result.width, result.height) == (-50, 20, 640, 480)
    assert result.monitor_count == 2
    assert result.path.exists()


def test_capture_full_desktop_uses_virtual_monitor(monkeypatch, tmp_path):
    _set_fake_capture(monkeypatch, tmp_path)

    result = screen_capture.capture_full_desktop(tmp_path)

    assert result.mode == "full_desktop"
    assert result.window is None
    assert (result.left, result.top) == (-1920, 0)
    assert result.monitor_count == 2
    assert result.path.exists()


def test_capture_each_monitor_saves_one_image_per_monitor(monkeypatch, tmp_path):
    _set_fake_capture(monkeypatch, tmp_path)

    captures = screen_capture.capture_each_monitor(tmp_path)

    assert len(captures) == 2
    assert [capture.monitor_index for capture in captures] == [1, 2]
    assert [(capture.left, capture.top) for capture in captures] == [(0, 0), (-1920, 0)]
    assert all(capture.path.exists() for capture in captures)


def test_cleanup_only_removes_expired_screen_capture_files(tmp_path):
    old_capture = tmp_path / "screen-old.png"
    old_capture.write_bytes(b"old")
    unrelated = tmp_path / "keep.png"
    unrelated.write_bytes(b"keep")

    import os
    import time

    old_time = time.time() - 61
    os.utime(old_capture, (old_time, old_time))

    assert screen_capture.cleanup_expired_captures(tmp_path, max_age_seconds=60) == 1
    assert not old_capture.exists()
    assert unrelated.exists()
