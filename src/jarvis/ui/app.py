"""Entry point for the Qt desktop UI. Run with `uv run python -m jarvis.ui`."""

import sys

from PySide6.QtWidgets import QApplication

from jarvis.setup import build_agent
from jarvis.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    agent = build_agent()
    window = MainWindow(agent)
    window.showMaximized()
    sys.exit(app.exec())
