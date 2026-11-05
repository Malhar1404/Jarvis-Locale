"""The voice orb: a rotating sphere made of dots, drawn with plain QPainter - no 3D engine
needed. Deforms with an AudioLevel (step 2); clicking it asks to go full screen (step 3). Step 4
adds hand gestures (via a HandState): moving your index finger moves and squashes the orb, and
closing/opening your fist squeezes it then bursts it outward.
"""

import math
import random

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from jarvis.ui import theme
from jarvis.vision.hand_state import HandState
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

    # Audio reactivity (step 2)
    LEVEL_SMOOTHING = 0.82  # how slowly the displayed level follows the raw audio level
    PULSE_AMOUNT = 0.22  # uniform "breathing" size change at full volume
    RIPPLE_AMOUNT = 0.08  # smaller detail layered on top - keep well below PULSE_AMOUNT
    RIPPLE_BANDS = 4  # how many ripple bands wrap around the sphere
    WOBBLE_SPEED = 4.0  # radians/second the ripple travels

    # Finger-follow + squash (step 4a)
    CENTER_SMOOTHING = 0.80  # how slowly the orb's position chases your fingertip
    SQUASH_SENSITIVITY = 6.0  # how much movement speed turns into squash
    MAX_SQUASH = 0.35

    # Fist squeeze + burst (step 4b)
    SQUEEZE_MAX = 0.35  # how much smaller the orb gets while your fist is closed
    SQUEEZE_SMOOTHING = 0.85
    BURST_STRENGTH = 0.9  # how hard points kick outward when your hand opens
    BURST_DAMPING = 0.88  # friction slowing that kick down each tick
    BURST_SPRING = 0.18  # how hard each point is pulled back to its resting radius

    def __init__(
        self,
        level_source: AudioLevel | None = None,
        hand_source: HandState | None = None,
    ) -> None:
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

        self._hand_source = hand_source
        self._target_center = (0.5, 0.5)  # normalized fraction of this widget's size
        self._display_center = (0.5, 0.5)
        self._velocity = (0.0, 0.0)
        self._target_squeeze = 0.0  # 0 = resting size, up to SQUEEZE_MAX = fully squeezed
        self._display_squeeze = 0.0
        self._prev_pose = "none"
        # One outward "kick" per point, each with its own position and velocity along its own
        # radial direction - a tiny damped spring per point, not a single shared animation, so
        # the burst looks like it's coming apart rather than just uniformly growing.
        self._burst_scale = [1.0] * self.POINT_COUNT
        self._burst_velocity = [0.0] * self.POINT_COUNT

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.TICK_MS)

    def _tick(self) -> None:
        self._angle += math.radians(self.ROTATION_DEGREES_PER_TICK)
        self._time += self.TICK_MS / 1000
        target_level = self._level_source.value if self._level_source else 0.0
        self._display_level += (target_level - self._display_level) * (1 - self.LEVEL_SMOOTHING)
        self._tick_hand()
        self.update()

    def _tick_hand(self) -> None:
        pointer = self._hand_source.pointer if self._hand_source else None
        pose = self._hand_source.pose if self._hand_source else "none"
        self._target_center = pointer if pointer is not None else (0.5, 0.5)
        self._target_squeeze = self.SQUEEZE_MAX if pose == "fist" else 0.0

        if self._prev_pose == "fist" and pose == "open":
            self._trigger_burst()
        self._prev_pose = pose

        old_center = self._display_center
        new_x = old_center[0] + (self._target_center[0] - old_center[0]) * (
            1 - self.CENTER_SMOOTHING
        )
        new_y = old_center[1] + (self._target_center[1] - old_center[1]) * (
            1 - self.CENTER_SMOOTHING
        )
        self._velocity = (new_x - old_center[0], new_y - old_center[1])
        self._display_center = (new_x, new_y)

        self._display_squeeze += (self._target_squeeze - self._display_squeeze) * (
            1 - self.SQUEEZE_SMOOTHING
        )

        for i in range(self.POINT_COUNT):
            # A damped spring pulling each point's burst scale back toward 1.0 (its resting
            # radius) - the velocity decays via friction (BURST_DAMPING) and gets pulled back by
            # the spring force (BURST_SPRING), which together produce one outward overshoot that
            # settles, not an instant snap.
            self._burst_velocity[i] *= self.BURST_DAMPING
            self._burst_velocity[i] -= (self._burst_scale[i] - 1.0) * self.BURST_SPRING
            self._burst_scale[i] += self._burst_velocity[i]

    def _trigger_burst(self) -> None:
        for i in range(self.POINT_COUNT):
            self._burst_velocity[i] += random.uniform(0.6, 1.0) * self.BURST_STRENGTH

    def paintEvent(self, event) -> None:  # noqa: ARG002 (Qt's signature, event unused)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PANEL))

        center_x = self._display_center[0] * self.width()
        center_y = self._display_center[1] * self.height()
        scale = min(self.width(), self.height()) * 0.42
        cos_spin, sin_spin = math.cos(self._angle), math.sin(self._angle)
        cos_tilt, sin_tilt = math.cos(self._tilt), math.sin(self._tilt)
        accent = QColor(theme.ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)

        speed = math.hypot(*self._velocity)
        squash = min(speed * self.SQUASH_SENSITIVITY, self.MAX_SQUASH)
        move_angle = math.atan2(self._velocity[1], self._velocity[0]) if speed > 1e-5 else 0.0
        cos_m, sin_m = math.cos(move_angle), math.sin(move_angle)
        squeeze_factor = 1.0 - self._display_squeeze

        # Draw back-to-front so near dots overlap far ones correctly.
        points_and_longitudes = zip(self._points, self._longitudes, strict=True)
        projected = []
        for i, ((x, y, z), longitude) in enumerate(points_and_longitudes):
            spun_x = x * cos_spin + z * sin_spin
            spun_z = -x * sin_spin + z * cos_spin
            tilted_y = y * cos_tilt - spun_z * sin_tilt
            tilted_z = y * sin_tilt + spun_z * cos_tilt

            ripple = math.sin(longitude * self.RIPPLE_BANDS + self._time * self.WOBBLE_SPEED)
            bulge = self.PULSE_AMOUNT + ripple * self.RIPPLE_AMOUNT
            radial_scale = (1.0 + self._display_level * bulge) * squeeze_factor
            radial_scale *= self._burst_scale[i]
            px = spun_x * radial_scale
            py = tilted_y * radial_scale
            pz = tilted_z * radial_scale

            if squash > 0:
                # Squash along the direction of movement, stretch a little across it - the
                # classic animation trick that sells something as actually moving, not sliding.
                along = px * cos_m + py * sin_m
                across = -px * sin_m + py * cos_m
                along *= 1 - squash
                across *= 1 + squash * 0.5
                px = along * cos_m - across * sin_m
                py = along * sin_m + across * cos_m

            projected.append((px, py, pz))
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
