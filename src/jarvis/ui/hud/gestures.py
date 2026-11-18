"""Interactive mode: a hand-tracked cursor on the HUD.

What a pinch does depends on what is under the cursor when your fingers START closing (the rule
lives in vision/pinch.py, where it is tested without Qt):
    a button or text field  -> a quick pinch clicks it
    a panel (title bar or body) -> pinch, hold and move drags it; a quick pinch raises it

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
from jarvis.vision.hand_tracking import HAND_LOSS_GRACE_SECONDS, HandTracker
from jarvis.vision.pinch import GestureEvent, PinchInteraction, Point, Target
from jarvis.vision.pointer import OneEuroFilter2D, map_to_screen

FRAME_MS = 16  # the UI timer; the camera gives new samples less often (see _tick)

# Sensitivity: only this middle part of the camera image covers the whole screen. 0.25..0.75 is a
# 2x gain: moving your hand half the image width crosses the screen. A smaller region = more
# sensitive (but amplifies shake). Tune with examples/phase7b_tune_cursor.py.
ACTIVE_LOW, ACTIVE_HIGH = 0.25, 0.75

# One Euro filter, "steady" preset (see jarvis/vision/pointer.py for what each knob does).
FILTER_MIN_CUTOFF = 1.0  # Hz: lower = steadier when still
# Higher = less lag when you flick. 0.02 was too high on real recordings: landmark noise by itself
# looks like fast motion, which opened the filter and left only 6-16% of the shake removed.
FILTER_BETA = 0.004
FILTER_D_CUTOFF = 1.0


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
        color.setAlpha(150)
        p.setPen(QPen(color, 1))
        p.setBrush(color if self.pinching else Qt.BrushStyle.NoBrush)
        p.drawEllipse(self.pos_, 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(self.pos_, 2.5 if not self.pinching else 4, 2.5 if not self.pinching else 4)
        p.end()


class GestureController(QObject):
    def __init__(self, desk: QWidget, overlay: CursorOverlay) -> None:
        super().__init__(desk)
        self._desk = desk
        self._overlay = overlay
        self._hand = HandState()
        self._tracker = HandTracker(self._hand)
        self._filter = OneEuroFilter2D(FILTER_MIN_CUTOFF, FILTER_BETA, FILTER_D_CUTOFF)
        self._interaction = PinchInteraction(self._classify)
        self._last_seq = -1  # which camera sample the filter has already seen
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.enabled = False
        self._pos: QPointF | None = None
        self._tracking_lost_at: float | None = None
        self._pinching = False
        self._grabbed: FloatingPanel | None = None
        self._drag_origin: QPoint | None = None  # where the grabbed panel was, to restore on cancel
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
            self._cancel_gesture()
            self._tracker.stop()
            self._overlay.hide()
            self._pos = None
            self._tracking_lost_at = None
            self._filter.reset()

    def _tick(self) -> None:
        point = self._hand.pinch_point or self._hand.pointer
        if point is None:  # hand left the camera view
            now = time.monotonic()
            if self._tracking_lost_at is None:
                self._tracking_lost_at = now
            if now - self._tracking_lost_at >= HAND_LOSS_GRACE_SECONDS:
                self._cancel_gesture()
                self._pos = None
                self._filter.reset()  # the cursor reappears at the hand, not sliding in
                self._overlay.set_cursor(None, pinching=False, grabbing=False)
            else:  # a brief dropout: hold the cursor (and any pinch) where it is
                self._overlay.set_cursor(
                    self._pos, pinching=self._pinching, grabbing=self._dragging
                )
            return
        self._tracking_lost_at = None
        # This timer ticks ~60x/s but the camera delivers ~30 samples/s. Handle each camera sample
        # exactly once, at the time it was captured - not once per tick - or the amount of
        # smoothing (and the pinch debounce, which counts frames) would depend on how the two
        # clocks happen to line up.
        if self._hand.seq != self._last_seq or self._pos is None:
            self._last_seq = self._hand.seq
            x, y = map_to_screen(
                point, self._desk.width(), self._desk.height(), ACTIVE_LOW, ACTIVE_HIGH
            )
            stamp = self._hand.timestamp
            t = time.monotonic() if stamp is None else stamp
            self._pos = QPointF(*self._filter(x, y, t))
            value = self._hand.pinch_value
            events = self._interaction.update(
                t, (self._pos.x(), self._pos.y()), 1.0 if value is None else value
            )
            for event in events:
                self._apply(event)
        self._overlay.set_cursor(
            self._pos, pinching=self._interaction.pinched, grabbing=self._dragging
        )

    # -- what is under the cursor (asked once per pinch, see vision/pinch.py) --------------
    def _classify(self, pos: Point) -> Target:
        widget = self._desk.childAt(QPoint(int(pos[0]), int(pos[1])))
        while widget is not None and widget is not self._desk:
            if isinstance(widget, QAbstractButton):
                return "button", widget
            if isinstance(widget, QLineEdit):
                return "field", widget
            if isinstance(widget, FloatingPanel):
                return "panel", widget
            widget = widget.parentWidget()
        return "none", None

    # -- turning the pure gesture events into widget actions -------------------------------
    def _apply(self, event: GestureEvent) -> None:
        kind = event.kind
        widget = event.target[1] if event.target is not None else None
        point = QPoint(round(event.pos[0]), round(event.pos[1]))
        if kind == "press":
            self._pinching = True
        elif kind == "drag_start" and isinstance(widget, FloatingPanel):
            self._grabbed, self._dragging = widget, True
            self._drag_origin = widget.pos()
            # point is where the pinch closed: the panel then moves by how far the cursor
            # travels from there, so the cursor's drift while closing never shifts the panel.
            widget.begin_drag(point)
        elif kind == "drag" and self._grabbed is not None:
            self._grabbed.drag_to(point)
            self._overlay.raise_()
        elif kind == "drop" and self._grabbed is not None:
            self._grabbed.drag_to(point)
            self._grabbed.end_drag()
        elif kind == "click":
            if isinstance(widget, QAbstractButton) and widget.isEnabled():
                widget.click()
            elif isinstance(widget, QLineEdit):
                widget.setFocus()
        elif kind == "tap" and isinstance(widget, FloatingPanel):
            widget.bring_to_front()
        elif kind == "release":
            self._pinching = False
            self._dragging = False
            self._grabbed = None
            self._drag_origin = None

    def _cancel_gesture(self) -> None:
        """Tracking was lost mid-pinch: put a half-dragged panel back instead of dropping it
        somewhere random, and never click.
        """
        self._interaction.cancel()
        if self._dragging and self._grabbed is not None:
            self._grabbed.end_drag()
            if self._drag_origin is not None:
                self._grabbed.move_clamped(self._drag_origin)
        self._pinching = False
        self._dragging = False
        self._grabbed = None
        self._drag_origin = None
