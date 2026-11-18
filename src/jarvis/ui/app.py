"""Entry point for the Qt desktop UI. Run with `uv run python -m jarvis.ui`.

Opens the full-screen HUD (ui/hud/). Add `--classic` for the older single-window UI
(ui/main_window.py), kept until the HUD has replaced it for good.
"""

import sys

from PySide6.QtWidgets import QApplication

from jarvis.safety.tiers import get_risk_tier
from jarvis.setup import build_agent, build_tools
from jarvis.ui import single_instance


def run() -> None:
    single_instance.acquire_or_exit()  # before QApplication - no point opening a window to close it
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # closing to the tray must not end the app
    tools = build_tools()
    agent = build_agent(tools)
    if "--classic" in sys.argv:
        from jarvis.ui.main_window import MainWindow

        window = MainWindow(agent, tool_names=[t.name for t in tools])
        window.showMaximized()
    else:
        from jarvis.ui.hud.window import HudWindow

        window = HudWindow(agent, tool_tiers={t.name: get_risk_tier(t).value for t in tools})
        window.showFullScreen()
    sys.exit(app.exec())
