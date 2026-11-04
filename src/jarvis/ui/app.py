"""Entry point for the Qt desktop UI. Run with `uv run python -m jarvis.ui`."""

import sys

from PySide6.QtWidgets import QApplication

from jarvis.setup import build_agent, build_tools
from jarvis.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # closing to the tray must not end the app
    tools = build_tools()
    agent = build_agent(tools)
    window = MainWindow(agent, tool_names=[t.name for t in tools])
    window.showMaximized()
    sys.exit(app.exec())
