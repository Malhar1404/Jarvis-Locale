"""Phase 7, the voice orb, step 1: just the rotating dotted sphere, no audio or gestures yet.
A plain QPainter widget - no 3D engine, no new dependency.

Run with:  uv run python examples/phase7_step4_orb.py
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from jarvis.ui import theme
from jarvis.ui.orb import Orb

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Jarvis - orb test")
window.setStyleSheet(f"QMainWindow {{ background-color: {theme.BG}; }}")
window.setCentralWidget(Orb())
window.resize(500, 500)
window.show()
sys.exit(app.exec())
