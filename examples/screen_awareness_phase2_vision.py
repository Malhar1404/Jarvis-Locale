"""Capture the active window, then ask the local Qwen3-VL model about it.

Example:
    uv run python examples/screen_awareness_phase2_vision.py "Explain this error"
"""

import sys
import time

from jarvis.vision.analysis import DEFAULT_SCREEN_QUESTION, analyze_screenshot
from jarvis.vision.screen_capture import capture_active_window

question = " ".join(sys.argv[1:]) or DEFAULT_SCREEN_QUESTION
print("Focus the window to inspect. Capturing in 3 seconds...")
time.sleep(3)
capture = capture_active_window()
print(f"Captured {capture.width}x{capture.height}. Asking Qwen3-VL...\n")
print(analyze_screenshot(capture.path, question))
