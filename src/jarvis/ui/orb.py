"""The voice orb: a rotating sphere made of dots, drawn with plain QPainter - no 3D engine
needed. Step 1 only proves the rotating visual; audio-reactivity and gestures come later.
"""

import math

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from jarvis.ui import theme


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
    POINT_COUNT = 400
    TILT_DEGREES = 25
    ROTATION_DEGREES_PER_TICK = 0.6
    TICK_MS = 33  # ~30fps

    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)

        self._points = _fibonacci_sphere(self.POINT_COUNT)
        self._angle = 0.0
        self._tilt = math.radians(self.TILT_DEGREES)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.TICK_MS)

    def _tick(self) -> None:
        self._angle += math.radians(self.ROTATION_DEGREES_PER_TICK)
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
        for x, y, z in self._points:
            spun_x = x * cos_spin + z * sin_spin
            spun_z = -x * sin_spin + z * cos_spin
            tilted_y = y * cos_tilt - spun_z * sin_tilt
            tilted_z = y * sin_tilt + spun_z * cos_tilt
            projected.append((spun_x, tilted_y, tilted_z))
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
