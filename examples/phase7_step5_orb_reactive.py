"""Phase 7, the voice orb, step 2: audio-reactive shape - click Speak and watch the orb deform
in time with the sentence as Piper actually plays it.

speak() runs on a background thread (it blocks until playback finishes) so the Qt event loop -
and the orb's own repaint timer - keeps running smoothly while it talks. The thread only ever
writes a float the orb's timer reads; see jarvis.voice.audio_level.AudioLevel for why that's
enough without a lock or a Qt signal per audio block.

Run with:  uv run python examples/phase7_step5_orb_reactive.py
"""

import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from jarvis.ui import theme
from jarvis.ui.orb import Orb
from jarvis.voice.audio_level import AudioLevel
from jarvis.voice.tts import speak

TEXT = "Hello! Watch the orb react while I speak this sentence out loud to you."

level = AudioLevel()


class _SpeechBridge(QObject):
    """speak() runs on a background thread - it must never touch a widget directly, so it signals
    back to the GUI thread instead (the same rule as jarvis.ui.worker.AgentWorker).
    """

    finished = Signal()


app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Jarvis - orb audio-reactive test")
window.setStyleSheet(f"QMainWindow {{ background-color: {theme.BG}; }}")

orb = Orb(level_source=level)
button = QPushButton("Speak")
bridge = _SpeechBridge()
bridge.finished.connect(lambda: button.setEnabled(True))


def on_click() -> None:
    button.setEnabled(False)

    def run() -> None:
        speak(TEXT, level)
        bridge.finished.emit()

    threading.Thread(target=run, daemon=True).start()


button.clicked.connect(on_click)

central = QWidget()
layout = QVBoxLayout(central)
layout.addWidget(orb)
layout.addWidget(button)
window.setCentralWidget(central)
window.resize(500, 560)
window.show()
sys.exit(app.exec())
