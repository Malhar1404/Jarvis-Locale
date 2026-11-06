"""On-demand Windows screen capture primitives for the Screen Awareness skill.

This module deliberately knows nothing about LangGraph or Ollama.  It provides a small,
testable boundary around Windows window coordinates and MSS image capture; later phases will
turn its result into tool output and visual context.
"""

import ctypes
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import win32gui
from mss import mss, tools

from jarvis.config import SCREEN_CAPTURE_DIR, SCREEN_CAPTURE_MAX_AGE_SECONDS

CaptureMode = Literal["active_window", "full_desktop"]

logger = logging.getLogger(__name__)


class ScreenCaptureError(RuntimeError):
    """Raised when Windows cannot provide a valid capture target or MSS cannot capture it."""


@dataclass(frozen=True)
class WindowInfo:
    """Physical-pixel bounds and identifying details for the current foreground window."""

    handle: int
    title: str
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class ScreenCapture:
    """Metadata for one saved screenshot.  Pixel coordinates may be negative on extra monitors."""

    mode: CaptureMode
    path: Path
    width: int
    height: int
    left: int
    top: int
    monitor_count: int
    window: WindowInfo | None = None


def enable_per_monitor_dpi_awareness() -> None:
    """Ask Windows for physical-pixel coordinates before reading window bounds.

    Windows otherwise may virtualize ``GetWindowRect`` for a non-DPI-aware process while MSS
    captures physical pixels.  Calling this is harmless when the process was already configured
    (Windows simply rejects the second request), so no failure needs to escape to the caller.
    """
    user32 = ctypes.windll.user32
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 is -4.  It supports mixed-DPI monitors.
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except AttributeError:
        # Available on older Windows versions that do not expose the newer context API.
        user32.SetProcessDPIAware()


def get_active_window() -> WindowInfo:
    """Return the current foreground window's title and physical-pixel bounding rectangle."""
    handle = win32gui.GetForegroundWindow()
    if not handle or not win32gui.IsWindow(handle):
        raise ScreenCaptureError("No active window is available to capture.")

    left, top, right, bottom = win32gui.GetWindowRect(handle)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise ScreenCaptureError("The active window has no visible capture area.")

    return WindowInfo(
        handle=handle,
        title=win32gui.GetWindowText(handle),
        left=left,
        top=top,
        width=width,
        height=height,
    )


def capture_active_window(output_dir: Path | None = None) -> ScreenCapture:
    """Capture only the current active window and save it as a temporary PNG."""
    window = get_active_window()
    return _capture(
        mode="active_window",
        region={
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
        },
        output_dir=output_dir,
        window=window,
    )


def capture_full_desktop(output_dir: Path | None = None) -> ScreenCapture:
    """Capture the complete virtual desktop, including every attached monitor."""
    enable_per_monitor_dpi_awareness()
    with mss() as screen:
        # MSS monitor zero is its virtual monitor: the bounding rectangle of every display.
        virtual_desktop = dict(screen.monitors[0])
    return _capture(mode="full_desktop", region=virtual_desktop, output_dir=output_dir, window=None)


def cleanup_expired_captures(
    output_dir: Path = SCREEN_CAPTURE_DIR, max_age_seconds: int = SCREEN_CAPTURE_MAX_AGE_SECONDS
) -> int:
    """Delete only this module's expired PNGs and return how many were removed."""
    if not output_dir.exists():
        return 0

    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in output_dir.glob("screen-*.png"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError as exc:
            logger.warning("Could not remove expired screen capture %s: %s", path.name, exc)
    return removed


def _capture(
    *,
    mode: CaptureMode,
    region: dict[str, int],
    output_dir: Path | None,
    window: WindowInfo | None,
) -> ScreenCapture:
    enable_per_monitor_dpi_awareness()
    destination = output_dir or SCREEN_CAPTURE_DIR
    destination.mkdir(parents=True, exist_ok=True)
    cleanup_expired_captures(destination)

    try:
        with mss() as screen:
            monitor_count = len(screen.monitors) - 1
            image = screen.grab(region)
    except Exception as exc:  # MSS exceptions vary by Windows/display-driver version.
        raise ScreenCaptureError(f"Could not capture {mode.replace('_', ' ')}: {exc}") from exc

    path = destination / f"screen-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}.png"
    try:
        tools.to_png(image.rgb, image.size, output=str(path))
    except OSError as exc:
        raise ScreenCaptureError(f"Could not save screen capture: {exc}") from exc

    return ScreenCapture(
        mode=mode,
        path=path,
        width=image.width,
        height=image.height,
        left=region["left"],
        top=region["top"],
        monitor_count=monitor_count,
        window=window,
    )
