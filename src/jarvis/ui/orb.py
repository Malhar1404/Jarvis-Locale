"""The voice orb: a rotating sphere made of dots, drawn with plain QPainter - no 3D engine
needed. Deforms with an AudioLevel (step 2); clicking it asks to go full screen (step 3) - the
window decides what that actually means. Gestures come later.
"""

import math

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from jarvis.ui import theme
from jarvis.voice.audio_level import AudioLevel


def _fibonacci_sphere(count: int) -> list[tuple[float, float, float]]:
    """count points evenly spread on a unit sphere (the "sunflower seed" method: a point's
    height step is constant while its angle advances by the golden angle each time, which is
    irrational enough that points never line up into visible rings).
    """
    golden_angle = math.pi * (3 - math.sqrt(5))
    points = []
    for i in range(count):
        y = 1 - (i / (count - 1)) * 2  # 1 -> -1
        radius_at_y = math.sqrt(max(0.0, 1 - y * y))
        theta = golden_angle * i
        points.append((math.cos(theta) * radius_at_y, y, math.sin(theta) * radius_at_y))
    return points


class Orb(QWidget):
    clicked = Signal()

    POINT_COUNT = 400
    TILT_DEGREES = 25
    ROTATION_DEGREES_PER_TICK = 0.6
    TICK_MS = 33  # ~30fps
    LEVEL_SMOOTHING = 0.82  # how slowly the displayed level follows the raw audio level
    PULSE_AMOUNT = 0.22  # uniform "breathing" size change at full volume
    RIPPLE_AMOUNT = 0.08  # smaller detail layered on top - keep well below PULSE_AMOUNT
    RIPPLE_BANDS = 4  # how many ripple bands wrap around the sphere
    WOBBLE_SPEED = 4.0  # radians/second the ripple travels

    def __init__(self, level_source: AudioLevel | None = None) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._points = _fibonacci_sphere(self.POINT_COUNT)
        # Each point's longitude (its angle around the Y axis) - used so nearby points ripple
        # together as a wave traveling around the sphere, instead of each wobbling independently
        # at random (which just looks like noise and destroys the sphere's silhouette).
        self._longitudes = [math.atan2(z, x) for x, _y, z in self._points]
        self._angle = 0.0
        self._tilt = math.radians(self.TILT_DEGREES)
        self._time = 0.0

        self._level_source = level_source
        self._display_level = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.TICK_MS)

    def _tick(self) -> None:
        self._angle += math.radians(self.ROTATION_DEGREES_PER_TICK)
        self._time += self.TICK_MS / 1000
        target_level = self._level_source.value if self._level_source else 0.0
        self._display_level += (target_level - self._display_level) * (1 - self.LEVEL_SMOOTHING)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002 (Qt's signature, event unused)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PANEL))

        center_x, center_y = self.width() / 2, self.height() / 2
        scale = min(self.width(), self.height()) * 0.42
        cos_spin, sin_spin = math.cos(self._angle), math.sin(self._angle)
        cos_tilt, sin_tilt = math.cos(self._tilt), math.sin(self._tilt)
        accent = QColor(theme.ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)

        # Draw back-to-front so near dots overlap far ones correctly.
        projected = []
        for (x, y, z), longitude in zip(self._points, self._longitudes, strict=True):
            spun_x = x * cos_spin + z * sin_spin
            spun_z = -x * sin_spin + z * cos_spin
            tilted_y = y * cos_tilt - spun_z * sin_tilt
            tilted_z = y * sin_tilt + spun_z * cos_tilt

            ripple = math.sin(longitude * self.RIPPLE_BANDS + self._time * self.WOBBLE_SPEED)
            bulge = self.PULSE_AMOUNT + ripple * self.RIPPLE_AMOUNT
            radial_scale = 1.0 + self._display_level * bulge
            projected.append(
                (spun_x * radial_scale, tilted_y * radial_scale, tilted_z * radial_scale)
            )
        projected.sort(key=lambda p: p[2])

        for px, py, pz in projected:
            depth = (pz + 1) / 2  # 0 = far side, 1 = near side
            screen_x = center_x + px * scale
            screen_y = center_y - py * scale
            dot_radius = 1.0 + depth * 2.5

            color = QColor(accent)
            color.setAlphaF(0.15 + depth * 0.75)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(screen_x, screen_y), dot_radius, dot_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
