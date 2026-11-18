"""The arc reactor: the HUD's centrepiece, drawn entirely with QPainter (no image files).

Layers, from the outside in:
    sound-wave ring   72 bars pointing outward, driven by FFT bands of Jarvis's own voice
    thin ring + rotating tick ring
    10 glowing coil segments
    dark inner housing with a spinning dashed ring
    pulsing white-hot core

The bars are mirrored left/right (bass at the top, treble at the bottom on both sides), which is
what makes a voice look like a symmetrical, "breathing" shape instead of a random scatter.

Smoothing: bars jump up fast (attack) and fall slowly (release). Raw FFT values change every
~20 ms and look jittery; this is the same trick every music visualizer uses.
"""

import math
import time

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from jarvis.ui.hud.style import STATE_COLORS
from jarvis.voice.audio_spectrum import AudioSpectrum

BAR_COUNT = 72
FRAME_MS = 16  # ~60 fps
ATTACK = 0.6  # how much of the gap to a *higher* target a bar closes per frame
RELEASE = 0.12  # ... and to a lower one - small, so bars fall gently
SPEAKING_HOLD = 0.5  # s of silence before "speaking" ends (gaps between words don't flicker it)
VOICE_THRESHOLD = 0.02  # AudioSpectrum.value above this counts as "Jarvis is talking"


class ArcReactor(QWidget):
    state_changed = Signal(str)  # the *shown* state, including the auto-detected "speaking"

    def __init__(self, parent: QWidget, spectrum: AudioSpectrum) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # clicks pass through
        self._spectrum = spectrum
        self._state = "idle"  # what the window says: idle / listening / thinking / waiting
        self._shown = "idle"
        self._bars = np.zeros(BAR_COUNT)
        self._level = 0.0
        self._last_voice = 0.0
        self._t0 = time.monotonic()
        # mirror index: bar i shows band _mirror[i] (0..35 down the right, 35..0 up the left)
        half = BAR_COUNT // 2
        scale = spectrum.band_count / half
        self._mirror = np.array(
            [int((i if i < half else BAR_COUNT - 1 - i) * scale) for i in range(BAR_COUNT)]
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(FRAME_MS)

    def set_state(self, state: str) -> None:
        self._state = state

    # -- animation -----------------------------------------------------------------------
    def _tick(self) -> None:
        now = time.monotonic()
        t = now - self._t0
        if self._spectrum.value > VOICE_THRESHOLD:
            self._last_voice = now
        speaking = now - self._last_voice < SPEAKING_HOLD and self._state != "listening"
        shown = "speaking" if speaking else self._state
        if shown != self._shown:
            self._shown = shown
            self.state_changed.emit(shown)

        target = self._targets(shown, t)
        rising = target > self._bars
        self._bars = np.where(
            rising,
            self._bars + (target - self._bars) * ATTACK,
            self._bars + (target - self._bars) * RELEASE,
        )
        self._level += (self._spectrum.value - self._level) * 0.25
        self.update()

    def _targets(self, shown: str, t: float) -> np.ndarray:
        if shown == "speaking":
            return self._spectrum.bands[self._mirror]
        i = np.arange(BAR_COUNT)
        if shown == "thinking":  # a bright "comet" sweeping around the ring
            angle = i / BAR_COUNT * 2 * math.pi
            comet = np.maximum(0.0, np.cos(angle - t * 3.0)) ** 10
            return 0.05 + 0.45 * comet
        if shown == "waiting":  # slow, even pulse - "your turn"
            return np.full(BAR_COUNT, 0.12 + 0.1 * (1 + math.sin(t * 2.2)) / 2)
        if shown == "listening":  # gentle ripple; deliberately NOT driven by your microphone
            return 0.08 + 0.05 * np.sin(t * 3.0 + i * 0.35)
        return 0.04 + 0.02 * np.sin(t * 1.2 + i * 0.25)  # idle: barely breathing

    # -- painting ------------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = time.monotonic() - self._t0
        color = QColor(STATE_COLORS.get(self._shown, STATE_COLORS["idle"]))
        r = min(self.width(), self.height()) / 2
        p.translate(self.width() / 2, self.height() / 2)

        def with_alpha(alpha: int) -> QColor:
            c = QColor(color)
            c.setAlpha(max(0, min(255, alpha)))
            return c

        # Soft halo behind everything.
        halo = QRadialGradient(QPointF(0, 0), r)
        halo.setColorAt(0.0, with_alpha(int(70 + 90 * self._level)))
        halo.setColorAt(0.45, with_alpha(25))
        halo.setColorAt(1.0, with_alpha(0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(0, 0), r, r)

        # Sound-wave ring.
        inner = r * 0.70
        max_len = r * 0.28
        pen = QPen(with_alpha(215), max(2.0, r * 0.012))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i, value in enumerate(self._bars):
            angle = i / BAR_COUNT * 2 * math.pi - math.pi / 2  # bar 0 points straight up
            length = 4 + float(value) * max_len
            dx, dy = math.cos(angle), math.sin(angle)
            p.drawLine(
                QPointF(dx * inner, dy * inner),
                QPointF(dx * (inner + length), dy * (inner + length)),
            )

        p.setBrush(Qt.BrushStyle.NoBrush)
        # Thin outer ring.
        p.setPen(QPen(with_alpha(110), 1))
        p.drawEllipse(QPointF(0, 0), r * 0.66, r * 0.66)

        # Rotating tick ring.
        p.save()
        p.rotate(t * 12)
        p.setPen(QPen(with_alpha(150), 1.2))
        for _ in range(72):
            p.drawLine(QPointF(0, -r * 0.62), QPointF(0, -r * 0.585))
            p.rotate(5)
        p.restore()

        # Coil segments: 10 thick arcs. Drawn twice - a wide faint pass is the glow.
        coil_r = r * 0.47
        rect = QRectF(-coil_r, -coil_r, coil_r * 2, coil_r * 2)
        for width, alpha in ((r * 0.16, 45), (r * 0.10, int(200 + 55 * self._level))):
            seg_pen = QPen(with_alpha(alpha), width)
            seg_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(seg_pen)
            for k in range(10):
                start = 90 + k * 36 + 4  # Qt arcs: degrees*16, counter-clockwise from 3 o'clock
                p.drawArc(rect, int(start * 16), int(28 * 16))

        # Inner housing.
        p.setPen(QPen(color, 2))
        p.setBrush(QColor(7, 13, 24))
        p.drawEllipse(QPointF(0, 0), r * 0.33, r * 0.33)

        # Spinning dashed ring.
        p.save()
        p.rotate(-t * 40)
        dash = QPen(with_alpha(150), 2)
        dash.setStyle(Qt.PenStyle.DashLine)
        p.setPen(dash)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r * 0.28, r * 0.28)
        p.restore()

        # Core: pulses on its own, and swells with Jarvis's voice.
        core_r = r * 0.24 * (1 + 0.05 * math.sin(t * 2.6) + 0.25 * self._level)
        core = QRadialGradient(QPointF(0, 0), core_r)
        core.setColorAt(0.0, QColor(255, 255, 255))
        core.setColorAt(0.25, QColor(230, 253, 255))
        core.setColorAt(0.55, color)
        core.setColorAt(1.0, with_alpha(0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(core)
        p.drawEllipse(QPointF(0, 0), core_r, core_r)
        p.end()
