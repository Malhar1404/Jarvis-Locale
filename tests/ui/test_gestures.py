import pytest
from PySide6.QtCore import QPoint, QPointF, QSize
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from jarvis.ui.hud.gestures import (
    ACTIVE_HIGH,
    ACTIVE_LOW,
    HAND_LOSS_GRACE_SECONDS,
    CursorOverlay,
    GestureController,
)
from jarvis.ui.hud.panel import FloatingPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _FakePanel:
    def __init__(self):
        self.ended_drag = False
        self.restored_position = None

    def end_drag(self):
        self.ended_drag = True

    def move_clamped(self, position):
        self.restored_position = position


def _controller(app):
    desk = QWidget()
    desk.resize(1000, 500)
    return GestureController(desk, CursorOverlay(desk))


def test_cursor_is_steady_while_the_hand_only_shakes(app):
    controller = _controller(app)
    positions = []
    for i in range(90):
        shake = 0.004 if i % 2 else -0.004  # +-8 px on this 1000 px desk at 2x gain
        controller._hand.set((0.5 + shake, 0.5), "other", (0.5 + shake, 0.5), False, i / 30)
        controller._tick()
        positions.append(controller._pos.x())

    settled = positions[30:]
    raw_peak_to_peak = 16.0
    assert max(settled) - min(settled) < 0.25 * raw_peak_to_peak  # at least 75% of shake removed
    assert abs(sum(settled) / len(settled) - 500) < 2.0  # ...and sits where the hand is


def test_one_camera_sample_is_filtered_once_even_if_the_timer_ticks_often(app):
    controller = _controller(app)
    controller._hand.set((0.4, 0.5), "other", (0.4, 0.5), False, 0.0)
    controller._tick()
    controller._hand.set((0.6, 0.5), "other", (0.6, 0.5), False, 1 / 30)
    controller._tick()
    after_first_tick = controller._pos.x()

    for _ in range(5):  # the 60 Hz timer ticks again before the camera has a new frame
        controller._tick()

    assert controller._pos.x() == after_first_tick


def test_tracking_loss_holds_cursor_then_cancels_drag(app, monkeypatch):
    desk = QWidget()
    overlay = CursorOverlay(desk)
    controller = GestureController(desk, overlay)
    panel = _FakePanel()
    controller._pos = QPointF(30, 40)
    controller._pinching = True
    controller._dragging = True
    controller._grabbed = panel
    controller._drag_origin = QPoint(10, 20)
    now = [100.0]
    monkeypatch.setattr("jarvis.ui.hud.gestures.time.monotonic", lambda: now[0])

    controller._hand.set(None, "none")
    controller._tick()

    assert controller._pos == QPointF(30, 40)
    assert overlay.pos_ == QPointF(30, 40)
    assert controller._pinching

    now[0] += HAND_LOSS_GRACE_SECONDS
    controller._tick()

    assert controller._pos is None
    assert not controller._pinching
    assert panel.ended_drag
    assert panel.restored_position == QPoint(10, 20)


class _Scene:
    """A desk with one floating panel (holding a button) and a hand that can be 'moved' by feeding
    camera samples to the controller at 30 fps, like the real tracker does.
    """

    def __init__(self, app):
        self.desk = QWidget()
        self.desk.resize(1000, 600)
        self.clicks = 0
        body = QWidget()
        layout = QVBoxLayout(body)
        self.button = QPushButton("go")
        self.button.clicked.connect(self._clicked)
        layout.addWidget(self.button)
        layout.addStretch()
        self.panel = FloatingPanel(self.desk, "t", "TITLE", "#00e5ff", body, QSize(320, 220))
        self.panel.move(100, 100)
        self.overlay = CursorOverlay(self.desk)
        self.controller = GestureController(self.desk, self.overlay)
        self.desk.show()
        self.overlay.setGeometry(self.desk.rect())
        self.overlay.show()  # on top of everything: hit-testing must see straight through it
        self.overlay.raise_()
        app.processEvents()
        self.frame = 0

    def _clicked(self) -> None:
        self.clicks += 1

    def at(self, widget: QWidget, local: QPoint | None = None) -> tuple[float, float]:
        point = widget.mapTo(self.desk, local or widget.rect().center())
        return point.x(), point.y()

    def feed(self, x: float, y: float, value: float) -> None:
        low, high = ACTIVE_LOW, ACTIVE_HIGH
        cam = (
            low + x / self.desk.width() * (high - low),
            low + y / self.desk.height() * (high - low),
        )
        self.controller._hand.set(cam, "other", cam, False, self.frame / 30, pinch_value=value)
        self.frame += 1
        self.controller._tick()

    def hold_still(self, x, y, frames=30):
        for _ in range(frames):
            self.feed(x, y, 1.0)

    def pinch(self, x, y, drift=(0.0, 0.0), hold=6, move=(0.0, 0.0), move_frames=0):
        """Fingers close (cursor drifts by `drift`), hold, maybe move, then open (drifts back)."""
        for i, value in enumerate([0.75, 0.4, 0.1]):
            f = (i + 1) / 3
            self.feed(x + drift[0] * f, y + drift[1] * f, value)
        cx, cy = x + drift[0], y + drift[1]
        for _ in range(hold):
            self.feed(cx, cy, 0.1)
        for i in range(move_frames):
            f = (i + 1) / move_frames
            self.feed(cx + move[0] * f, cy + move[1] * f, 0.1)
        ex, ey = cx + move[0], cy + move[1]
        for i, value in enumerate([0.5, 0.9, 1.0]):
            f = (i + 1) / 3
            self.feed(ex + (x - ex) * f, ey + (y - ey) * f, value)
        for _ in range(10):
            self.feed(x, y, 1.0)


def test_a_tap_on_a_button_clicks_it_and_does_not_move_the_panel(app):
    scene = _Scene(app)
    x, y = scene.at(scene.button)
    start = scene.panel.pos()

    scene.hold_still(x, y)
    scene.pinch(x, y, drift=(35, 0))  # the cursor drifts 35 px (more than the button is wide)

    assert scene.clicks == 1
    assert scene.panel.pos() == start


def test_dragging_a_panel_by_its_title_bar_moves_it_and_clicks_nothing(app):
    scene = _Scene(app)
    x, y = scene.at(scene.panel, QPoint(150, 20))  # the title bar, away from the hide button
    start = scene.panel.pos()

    scene.hold_still(x, y)
    scene.pinch(x, y, drift=(30, 0), hold=4, move=(200, 60), move_frames=15)

    moved = scene.panel.pos() - start
    assert abs(moved.x() - 200) < 50  # follows the hand (a little lag from the smoothing)
    assert abs(moved.y() - 60) < 30
    assert scene.clicks == 0


def test_a_tap_on_a_panels_surface_does_not_drag_it(app):
    scene = _Scene(app)
    x, y = scene.at(scene.panel, QPoint(150, 20))
    start = scene.panel.pos()

    scene.hold_still(x, y)
    scene.pinch(x, y, drift=(40, 0))

    assert scene.panel.pos() == start
