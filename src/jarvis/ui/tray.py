"""The system tray icon. Lets closing the window hide Jarvis instead of quitting it - the
worker thread (and the Agent's conversation) keeps running in the background.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from jarvis.ui import theme


def make_icon() -> QIcon:
    """A small generated icon (no image asset needed): a cyan circle with a "J" on it."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(theme.ACCENT))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor(theme.BG))
    painter.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    painter.end()
    return QIcon(pixmap)


class Tray(QSystemTrayIcon):
    def __init__(self, window) -> None:
        super().__init__(make_icon())
        self._window = window
        self.setToolTip("Jarvis")

        menu = QMenu()
        self._toggle_action = menu.addAction("Hide Jarvis")
        self._toggle_action.triggered.connect(self._toggle_window)
        menu.addSeparator()
        menu.addAction("Quit Jarvis").triggered.connect(window.quit_app)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
        else:
            self._window.showMaximized()
            self._window.raise_()
            self._window.activateWindow()
        self.sync_toggle_text()

    def sync_toggle_text(self) -> None:
        """Call this whenever the window's visibility changed some other way (e.g. the user
        clicked the window's own close button), so the menu text doesn't go stale.
        """
        self._toggle_action.setText("Hide Jarvis" if self._window.isVisible() else "Show Jarvis")
