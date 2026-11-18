"""Phase 7b: preview the full HUD with a FAKE agent - no Ollama, no Piper, no screenshots taken.

The fake agent replays scripted AgentEvents with realistic pauses, so you can check every panel:
    type anything            -> thinking, then a streamed reply
    type "screen ..."        -> tool call, 2 fake screenshot thumbnails, vision results, reply
    type "delete ..."        -> approval pop-up (Allow / Deny), then a reply
    type "interactive mode on" / "... off" -> camera hand control (handled by the HUD itself)
While a reply streams, a synthetic "voice" (a few harmonics) feeds the arc reactor's FFT ring,
standing in for Piper - so the wave ring reacts exactly as it will to the real voice.

The HUD itself is the real one (jarvis.ui.hud.window.HudWindow); only the agent is fake.
Close: the × in the top bar hides to the tray; right-click the tray icon -> Quit Jarvis.

Run: uv run python examples/phase7b_hud_preview.py
"""

import sys
import threading
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from jarvis.agent.events import (
    ApprovalRequest,
    ScreenCaptured,
    ScreenShot,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
    VisionResult,
)
from jarvis.config import DATA_DIR
from jarvis.ui.hud.window import HudWindow

PREVIEW_DIR = DATA_DIR / "hud_preview"
VOICE_RATE = 22_050
speaking = threading.Event()


def make_fake_screenshot(path: Path, light: bool) -> None:
    """A tiny drawn 'screen' so the thumbnails have something to show."""
    image = QImage(1600, 900, QImage.Format.Format_RGB32)
    image.fill(QColor("#e9edf2" if light else "#11161f"))
    p = QPainter(image)
    p.fillRect(0, 0, 1600, 60, QColor("#cfd6de" if light else "#1c2330"))
    for row in range(12):
        width = 300 + (row * 137) % 700
        color = QColor("#94a3b8" if light else ["#3c6e91", "#8a6dbf", "#4a5568"][row % 3])
        p.fillRect(QRectF(160, 120 + row * 44, width, 18), color)
    if not light:
        p.fillRect(160, 700, 1300, 150, QColor("#0b0e14"))
        p.fillRect(190, 730, 900, 22, QColor("#ff5252"))
        p.fillRect(190, 770, 600, 22, QColor("#ff5252"))
    p.setPen(QColor("#00e5ff"))
    p.drawEllipse(QPointF(1500, 30), 12, 12)
    p.end()
    image.save(str(path))


class FakeAgent:
    """Has the same run()/resume() shape as jarvis.agent.runner.Agent."""

    def __init__(self, shots: list[ScreenShot]) -> None:
        self._shots = shots

    def run(self, text: str):
        yield Thinking(node="chatbot")
        time.sleep(1.2)
        lowered = text.lower()
        if "screen" in lowered:
            yield ToolCall(name="inspect_screen", args={"question": "what error is visible?"})
            time.sleep(0.4)
            yield ScreenCaptured(shots=self._shots)
            time.sleep(2.5)
            yield VisionResult(
                label="Monitor 1",
                text='VS Code. The terminal shows "ModuleNotFoundError: No module named '
                "'requests'\" from main.py line 3.",
                seconds=2.5,
            )
            time.sleep(1.8)
            yield VisionResult(label="Monitor 2", text="A browser with docs open.", seconds=1.8)
            yield ToolResult(name="inspect_screen", content="{}", status="ok")
            time.sleep(0.9)
            yield from self._reply(
                "Your terminal shows ModuleNotFoundError: no module named requests. "
                "Install it with uv add requests and run the script again."
            )
        elif "delete" in lowered:
            yield ToolCall(name="delete_file", args={"name": "old_notes.txt"})
            yield ApprovalRequest(
                name="delete_file", args={"name": "old_notes.txt"}, tier="always_ask"
            )
        else:
            yield from self._reply(
                "All systems are running normally. CPU load is low and there is plenty of "
                "memory free. Anything else?"
            )

    def resume(self, decision: str):
        time.sleep(0.5)
        if decision == "yes":
            yield ToolResult(name="delete_file", content="Deleted old_notes.txt.", status="ok")
            time.sleep(0.8)
            yield from self._reply("Done. old_notes.txt has been deleted.")
        else:
            yield ToolResult(name="delete_file", content="User denied.", status="error")
            time.sleep(0.8)
            yield from self._reply("Okay, I left the file alone.")

    def _reply(self, text: str):
        speaking.set()
        try:
            for word in text.split(" "):
                yield Token(text=word + " ")
                time.sleep(0.09)
            time.sleep(0.6)
        finally:
            speaking.clear()


def fake_voice(window: HudWindow) -> None:
    """Feeds the reactor's AudioSpectrum a vowel-like signal while 'speaking' is set: a base
    pitch plus overtones whose loudness wobbles like syllables. Real use: Piper's audio.
    """
    spectrum = window._spectrum  # the same object TTS playback writes to in the real app
    block = 512
    t = 0.0
    while True:
        time.sleep(block / VOICE_RATE)
        if not speaking.is_set():
            if spectrum.value:
                spectrum.reset()
            continue
        times = t + np.arange(block) / VOICE_RATE
        t = times[-1]
        syllable = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t) ** 2
        pitch = 120 + 25 * np.sin(2 * np.pi * 0.7 * t)
        signal = sum((0.5 / k) * np.sin(2 * np.pi * pitch * k * times) for k in (1, 2, 3, 5, 8, 13))
        spectrum.update((signal * 0.5 * syllable).astype(np.float32), VOICE_RATE)


def main() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    shots = []
    for index, light in ((1, False), (2, True)):
        path = PREVIEW_DIR / f"monitor{index}.png"
        make_fake_screenshot(path, light)
        size = "2560×1440" if index == 1 else "1920×1080"
        shots.append(ScreenShot(path=str(path), label=f"Monitor {index} · {size}"))

    tiers = {
        "get_time": "auto", "get_system_info": "auto", "set_volume": "auto",
        "set_brightness": "auto", "list_files": "auto", "read_file": "auto",
        "open_app": "ask_once", "write_file": "ask_once", "inspect_screen": "ask_once",
        "get_clipboard": "ask_once", "delete_file": "always_ask", "move_file": "always_ask",
    }  # fmt: skip
    window = HudWindow(FakeAgent(shots), tool_tiers=tiers)  # type: ignore[arg-type]
    threading.Thread(target=fake_voice, args=(window,), daemon=True).start()
    window.setWindowState(Qt.WindowState.WindowFullScreen)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
