"""Interactive mode: a hand-tracked cursor on the HUD. Pinch-and-move drags a panel; a quick
pinch (short, barely moving) "clicks" whatever button is under the cursor.

There are no fake OS mouse events here. The controller asks the desk which widget is under the
cursor (QWidget.childAt) and calls the same methods the mouse path uses - panel.begin_drag /
drag_to / end_drag, button.click(). That only works inside our own window, which is exactly
the scope we want: hand gestures can never click things in other apps.
"""

import time

from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QLineEdit, QWidget

from jarvis.ui import theme
from jarvis.ui.hud.panel import FloatingPanel
from jarvis.ui.hud.style import TEXT_DIM
from jarvis.vision.hand_state import HandState
from jarvis.vision.hand_tracking import HandTracker

FRAME_MS = 16
# Only the middle of the camera image maps to the whole screen, so you can reach the screen's
# edges without your hand leaving the camera's view.
ACTIVE_LOW, ACTIVE_HIGH = 0.15, 0.85
SMOOTHING = 0.35  # 0..1: how far the cursor moves toward the hand each frame (lower = calmer)
DRAG_START_PX = 12  # a pinch must move this far before it becomes a drag
CLICK_MAX_SECONDS = 0.45  # a pinch released sooner than this, without dragging, is a click


class CursorOverlay(QWidget):
    """Draws the hand cursor over everything. Transparent to the mouse, so it never blocks a
    click, and QWidget.childAt() looks straight through it.
    """

    def __init__(self, desk: QWidget) -> None:
        super().__init__(desk)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pos_: QPointF | None = None
        self.pinching = False
        self.grabbing = False
        self.hide()

    def set_cursor(self, pos: QPointF | None, *, pinching: bool, grabbing: bool) -> None:
        self.pos_, self.pinching, self.grabbing = pos, pinching, grabbing
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.pos_ is None:
            p.setPen(QColor(TEXT_DIM))
            p.drawText(
                self.rect().adjusted(0, 0, 0, -90),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                "Interactive mode: show your hand to the camera",
            )
            p.end()
            return
        color = QColor(theme.TOOL if self.grabbing else theme.ACCENT)
        glow = QColor(color)
        glow.setAlpha(60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(self.pos_, 26, 26)
        p.setPen(QPen(color, 2))
        p.setBrush(color if self.pinching else Qt.BrushStyle.NoBrush)
        radius = 9 if self.pinching else 15
        p.drawEllipse(self.pos_, radius, radius)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # small crosshair ticks
            start = QPointF(self.pos_.x() + dx * 20, self.pos_.y() + dy * 20)
            end = QPointF(self.pos_.x() + dx * 27, self.pos_.y() + dy * 27)
            p.drawLine(start, end)
        p.end()


class GestureController(QObject):
    def __init__(self, desk: QWidget, overlay: CursorOverlay) -> None:
        super().__init__(desk)
        self._desk = desk
        self._overlay = overlay
        self._hand = HandState()
        self._tracker = HandTracker(self._hand)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.enabled = False
        self._pos: QPointF | None = None
        self._pinching = False
        self._pinch_started = 0.0
        self._pinch_origin = QPointF()
        self._grabbed: FloatingPanel | None = None
        self._dragging = False

    def set_enabled(self, on: bool) -> None:
        if on == self.enabled:
            return
        self.enabled = on
        if on:
            self._tracker.start()  # the webcam is only ever on while this mode is on
            self._overlay.setGeometry(self._desk.rect())
            self._overlay.show()
            self._overlay.raise_()
            self._timer.start(FRAME_MS)
        else:
            self._timer.stop()
            self._release()
            self._tracker.stop()
            self._overlay.hide()
            self._pos = None

    def _tick(self) -> None:
        point = self._hand.pinch_point or self._hand.pointer
        if point is None:  # hand left the camera view
            self._release()
            self._pos = None
            self._overlay.set_cursor(None, pinching=False, grabbing=False)
            return
        target = self._to_desk(point)
        if self._pos is None:
            self._pos = target
        else:
            self._pos += (target - self._pos) * SMOOTHING

        pinching = self._hand.pinching
        if pinching and not self._pinching:
            self._press()
        elif pinching:
            self._hold()
        elif self._pinching:
            self._release(click=True)
        self._overlay.set_cursor(self._pos, pinching=pinching, grabbing=self._dragging)

    def _to_desk(self, point: tuple[float, float]) -> QPointF:
        def scale(value: float) -> float:
            return min(1.0, max(0.0, (value - ACTIVE_LOW) / (ACTIVE_HIGH - ACTIVE_LOW)))

        return QPointF(scale(point[0]) * self._desk.width(), scale(point[1]) * self._desk.height())

    def _press(self) -> None:
        self._pinching = True
        self._pinch_started = time.monotonic()
        self._pinch_origin = QPointF(self._pos)
        self._grabbed = self._panel_at(self._pos)
        self._dragging = False

    def _hold(self) -> None:
        if self._grabbed is None:
            return
        moved = (self._pos - self._pinch_origin).manhattanLength()
        if not self._dragging and moved > DRAG_START_PX:
            self._dragging = True
            self._grabbed.begin_drag(self._pinch_origin.toPoint())
        if self._dragging:
            self._grabbed.drag_to(self._pos.toPoint())
            self._overlay.raise_()

    def _release(self, *, click: bool = False) -> None:
        if not self._pinching:
            return
        if self._dragging and self._grabbed is not None:
            self._grabbed.end_drag()
        elif click and time.monotonic() - self._pinch_started < CLICK_MAX_SECONDS:
            self._click(self._pos)
        self._pinching = False
        self._dragging = False
        self._grabbed = None

    def _widget_at(self, pos: QPointF) -> QWidget | None:
        return self._desk.childAt(QPoint(int(pos.x()), int(pos.y())))

    def _panel_at(self, pos: QPointF) -> FloatingPanel | None:
        widget = self._widget_at(pos)
        while widget is not None and not isinstance(widget, FloatingPanel):
            widget = widget.parentWidget()
        return widget

    def _click(self, pos: QPointF) -> None:
        widget = self._widget_at(pos)
        while widget is not None and widget is not self._desk:
            if isinstance(widget, QAbstractButton):
                if widget.isEnabled():
                    widget.click()
                return
            if isinstance(widget, QLineEdit):
                widget.setFocus()
                return
            if isinstance(widget, FloatingPanel):
                widget.bring_to_front()
                return
            widget = widget.parentWidget()
