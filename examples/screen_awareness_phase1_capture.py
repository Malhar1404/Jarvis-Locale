"""Manually verify Phase 1 on this Windows desktop.

Focus any normal application after this script starts its countdown.  The active-window and
full-desktop images are saved beneath .data/screen_captures/ and are automatically pruned after
one hour on later captures.
"""

import time

from jarvis.vision.screen_capture import capture_active_window, capture_full_desktop


def describe(label: str, capture) -> None:
    print(f"{label}: {capture.width}x{capture.height} at ({capture.left}, {capture.top})")
    print(f"  monitors: {capture.monitor_count}; saved: {capture.path}")
    if capture.window is not None:
        print(f"  active window: {capture.window.title!r}")


print("Focus the window you want to capture. Capturing in 3 seconds...")
time.sleep(3)
describe("Active window", capture_active_window())
describe("Full desktop", capture_full_desktop())
