"""FloatingPanel: a see-through panel that sits on the HUD desk and can be dragged anywhere.

Dragging is three small steps, shared by the mouse (title bar) and the hand-gesture cursor:
    begin_drag(point)  remember where on the panel you grabbed it ("offset")
    drag_to(point)     move so that same spot stays under the pointer
    end_drag()         forget the offset
All points are in the desk's own coordinates, so the panel never needs to know about screens.
"""

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from jarvis.ui.hud.style import MONO, PANEL_BG, rgba


class _TitleBar(QWidget):
    """The grab handle. It only translates mouse events into the panel's drag steps."""

    def __init__(self, panel: "FloatingPanel") -> None:
        super().__init__(panel)
        self._panel = panel
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(40)

    def _desk_point(self, event: QMouseEvent) -> QPoint:
        return self._panel.parentWidget().mapFromGlobal(event.globalPosition().toPoint())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._panel.begin_drag(self._desk_point(event))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._panel.drag_to(self._desk_point(event))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: ARG002
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._panel.end_drag()


class FloatingPanel(QFrame):
    moved = Signal()  # position, size or visibility changed - the desk repaints the glow
    raised = Signal()  # came to the front - the desk keeps the cursor overlay above it
    hidden_by_user = Signal(str)  # the panel's own "–" button was clicked; carries its key

    def __init__(
        self,
        desk: QWidget,
        key: str,
        title: str,
        color: str,
        body: QWidget,
        size: QSize,
        *,
        subtitle: str = "",
        closable: bool = True,
        background: str = PANEL_BG,
    ) -> None:
        super().__init__(desk, objectName="floatingPanel")
        self.key = key
        self.color = color
        self._drag_offset: QPoint | None = None
        self.setStyleSheet(
            f"QFrame#floatingPanel {{ background-color: {background};"
            f" border: 1px solid {rgba(color, 120)}; border-radius: 10px; }}"
        )

        bar = _TitleBar(self)
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(14, 0, 8, 0)
        bar_row.setSpacing(8)
        grip = QLabel("⋮⋮")
        grip.setStyleSheet(f"color: {color}; font-size: 13px;")
        title_label = QLabel(title)
        title_font = QFont(MONO.split(",")[0])
        title_font.setPixelSize(11)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {color};")
        bar_row.addWidget(grip)
        bar_row.addWidget(title_label)
        if subtitle:
            bar_row.addWidget(QLabel(subtitle, objectName="panelSubtitle"))
        bar_row.addStretch()
        if closable:
            hide_button = QPushButton("–", objectName="panelHide")
            hide_button.setToolTip("Hide (bring it back from the dock)")
            hide_button.setCursor(Qt.CursorShape.PointingHandCursor)
            hide_button.clicked.connect(self._hide_by_user)
            bar_row.addWidget(hide_button)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {rgba(color, 50)}; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(bar)
        layout.addWidget(divider)
        layout.addWidget(body, 1)
        self.resize(size)

    # -- dragging (mouse and gestures both use these) --------------------------------------
    def begin_drag(self, desk_point: QPoint) -> None:
        self._drag_offset = desk_point - self.pos()
        self.bring_to_front()

    def drag_to(self, desk_point: QPoint) -> None:
        if self._drag_offset is not None:
            self.move_clamped(desk_point - self._drag_offset)

    def end_drag(self) -> None:
        self._drag_offset = None

    def move_clamped(self, top_left: QPoint) -> None:
        """Move, but never past the desk's edges - a panel dragged off-screen would be lost."""
        desk = self.parentWidget()
        x = max(0, min(top_left.x(), desk.width() - self.width()))
        y = max(0, min(top_left.y(), desk.height() - self.height()))
        self.move(x, y)

    def bring_to_front(self) -> None:
        self.raise_()
        self.raised.emit()

    # -- notify the desk so it can repaint the glow behind us ------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.bring_to_front()  # clicking anywhere on a panel brings it forward
        super().mousePressEvent(event)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.moved.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.moved.emit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.moved.emit()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.moved.emit()

    def _hide_by_user(self) -> None:
        self.hide()
        self.hidden_by_user.emit(self.key)
