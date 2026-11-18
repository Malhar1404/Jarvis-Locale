"""Turning a hand position from the camera into a steady point on the screen. Pure maths - no Qt,
no camera - so it can be tested with made-up shaky paths and replayed on recorded ones.

Two pieces:
    map_to_screen     camera coordinates (0..1) -> screen pixels, with a gain (see below)
    OneEuroFilter2D   removes shake without adding lag when you really move
"""

import math

Point = tuple[float, float]


def map_to_screen(
    point: Point, width: float, height: float, low: float = 0.25, high: float = 0.75
) -> Point:
    """Map a camera point to screen pixels. Only the camera region [low, high] (on each axis)
    covers the whole screen, and anything outside it clamps to the screen edge. A smaller region
    means a higher gain: with 0.25..0.75 a hand move of half the image width crosses the screen
    (2x), and the screen edges are reachable without your hand leaving the camera's view.
    """

    def scale(value: float) -> float:
        return min(1.0, max(0.0, (value - low) / (high - low)))

    return scale(point[0]) * width, scale(point[1]) * height


def _alpha(cutoff_hz: float, dt: float) -> float:
    """How far a low-pass filter moves toward a new sample: 0 = ignore it, 1 = copy it.

    A low-pass with cutoff f smooths with time constant tau = 1 / (2 pi f). Taking the gap dt
    between samples into account is what makes the result the same at 30 or 60 samples a second.
    """
    tau = 1.0 / (2.0 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter2D:
    """The "One Euro" filter (Casiez, Roussel, Vogel 2012) for a 2D point.

    The problem it solves: one fixed amount of smoothing is always a bad trade. Smooth a lot and
    the cursor lags when you move; smooth a little and it shakes when you hold still. So the
    amount of smoothing follows your speed:
        slow or still -> low cutoff  -> heavy smoothing  (shake disappears)
        fast          -> high cutoff -> light smoothing  (no lag when you flick)
    cutoff = min_cutoff + beta * speed

    Knobs (units: the point's own units, e.g. pixels, and seconds):
        min_cutoff  Hz. Lower = steadier when still, but a little slower to settle.
        beta        Higher = lag disappears sooner as you speed up (but a little more shake).
        d_cutoff    Hz. Smoothing for the speed estimate itself; 1.0 is almost always fine.
        max_gap     Seconds. A longer pause between samples (hand left the view) restarts the
                    filter, so the cursor appears at the hand instead of sliding in from far away.

    The speed is the length of the 2D velocity, so both axes share one cutoff. (Per-axis filters
    would smooth x and y by different amounts and bend diagonal moves.)
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.02,
        d_cutoff: float = 1.0,
        max_gap: float = 0.5,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.max_gap = max_gap
        self.reset()

    def reset(self) -> None:
        self._time: float | None = None
        self._raw: Point = (0.0, 0.0)  # last raw sample
        self._out: Point = (0.0, 0.0)  # last filtered output
        self._velocity: Point = (0.0, 0.0)  # smoothed velocity, units per second

    def __call__(self, x: float, y: float, t: float) -> Point:
        """Filter one sample taken at time t (seconds). Returns the steady point."""
        if self._time is None or t - self._time > self.max_gap:
            self._time, self._raw, self._out, self._velocity = t, (x, y), (x, y), (0.0, 0.0)
            return self._out
        dt = t - self._time
        if dt <= 0:  # the same sample again, or an older one: nothing new to learn from it
            return self._out

        a_velocity = _alpha(self.d_cutoff, dt)
        raw_vx = (x - self._raw[0]) / dt
        raw_vy = (y - self._raw[1]) / dt
        self._velocity = (
            self._velocity[0] + (raw_vx - self._velocity[0]) * a_velocity,
            self._velocity[1] + (raw_vy - self._velocity[1]) * a_velocity,
        )
        speed = math.hypot(*self._velocity)

        a = _alpha(self.min_cutoff + self.beta * speed, dt)
        self._out = (
            self._out[0] + (x - self._out[0]) * a,
            self._out[1] + (y - self._out[1]) * a,
        )
        self._raw = (x, y)
        self._time = t
        return self._out
