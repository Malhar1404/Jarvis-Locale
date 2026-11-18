"""Pinch gestures: telling a click, a drag and plain hand movement apart. Pure logic - no Qt, no
camera - so it is tested with made-up (and recorded) hand paths.

Two pieces:
    PinchDetector     "are the fingers pinched?" with hysteresis and a 2-frame debounce, and it
                      can say WHEN the fingers started closing / opening
    PinchInteraction  turns pinches into events: click, drag start / move / drop, tap

Why "when the fingers started closing" matters: closing your fingers moves the cursor too (the
point halfway between thumb and index tip shifts as the tips come together; in recordings, 35-50 px
across one tap - more than half a button). By the time the pinch is confirmed the cursor has
already left what you were aiming at. So the target is taken from the position history, from just
before the fingers began to close. The same trick on the way out gives the drop position.

The value fed in is the pinch ratio: thumb-to-index gap divided by palm size, so it works near or
far from the camera. About 1.0 for an open hand, below 0.3 for a pinch.
"""

import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

Point = tuple[float, float]
Target = tuple[str, object]  # (kind, widget): kind is "button", "field", "panel" or "none"

# Two thresholds (hysteresis): a pinch starts below ON and ends only above OFF. With one threshold,
# a gap hovering right at the line would flicker pinch / no-pinch every frame.
PINCH_ON = 0.30
PINCH_OFF = 0.45
CONFIRM_FRAMES = 2  # consecutive camera frames needed to start or end a pinch (~65 ms at 30 fps)
HISTORY_SECONDS = 0.8
ONSET_FRACTION = 0.2  # "started closing" = the last frame still within 20% of the open value

DRAG_START_PX = 14.0  # a pinch on a panel must move this far (after closing) to become a drag
CLICK_MAX_SECONDS = 0.8  # a pinch held longer than this is not a click
CLICK_SLOP_PX = 30.0  # ...and neither is one where the cursor wandered farther than this


class PinchDetector:
    def __init__(self, on: float = PINCH_ON, off: float = PINCH_OFF, confirm: int = CONFIRM_FRAMES):
        self.on, self.off, self.confirm = on, off, confirm
        self.reset()

    def reset(self) -> None:
        self.pinched = False
        self._streak = 0
        self._history: deque[tuple[float, float]] = deque()  # (time, value)

    def update(self, t: float, value: float) -> str | None:
        """Feed one camera sample. Returns "press" or "release" on the frame that confirms it."""
        self._history.append((t, value))
        while t - self._history[0][0] > HISTORY_SECONDS:
            self._history.popleft()
        if self.pinched:
            self._streak = self._streak + 1 if value >= self.off else 0
        else:
            self._streak = self._streak + 1 if value < self.on else 0
        if self._streak >= self.confirm:
            self.pinched = not self.pinched
            self._streak = 0
            return "press" if self.pinched else "release"
        return None

    def closing_onset(self) -> float:
        """Time the fingers began to close. Call right after a "press"."""
        samples = list(self._history)
        now = samples[-1][1]
        high = max(value for _, value in samples)
        cutoff = high - ONSET_FRACTION * (high - now)
        for t, value in reversed(samples):
            if value >= cutoff:  # the last frame that was still (almost) fully open
                return t
        return samples[-1][0]

    def opening_onset(self) -> float:
        """Time the fingers began to open. Call right after a "release"."""
        samples = list(self._history)
        now = samples[-1][1]
        low = min(value for _, value in samples)
        cutoff = low + ONSET_FRACTION * (now - low)
        for t, value in reversed(samples):
            if value <= cutoff:  # the last frame that was still (almost) fully closed
                return t
        return samples[-1][0]


@dataclass(frozen=True)
class GestureEvent:
    """What happened, and where (in the same units as the positions fed in).

    kind: "press"       a pinch was confirmed; pos = the aimed-at point, target = what is there
          "drag_start"  a panel drag begins; pos = the cursor now (the reference point)
          "drag"        the dragged panel should follow pos
          "drop"        the drag ends at pos
          "click"       a button or text field was clicked
          "tap"         a quick pinch on a panel's surface (bring it to the front)
          "release"     the pinch ended (always the last event of a pinch)
          "cancel"      tracking was lost mid-pinch
    """

    kind: str
    pos: Point
    target: Target | None = None


@dataclass
class _Press:
    target: Target
    lock: Point  # where the cursor was just before the fingers started closing
    anchor: Point  # where it was once the pinch closed: drag distance is measured from here
    onset: float  # time the fingers started closing
    dragging: bool = False


class PinchInteraction:
    """Decides click vs drag by WHAT IS UNDER THE CURSOR when the pinch starts, not by movement:
        "button" / "field"  -> click only (never drags)
        "panel"             -> drag only (a quick tap just raises it)
        anything else       -> nothing
    Movement can't be the rule: the cursor already moves 35-50 px by itself while the fingers
    close, so "moved far = drag" would turn every tap into a drag.

    classify(pos) -> (kind, widget) is supplied by the UI and called once per pinch.
    """

    def __init__(
        self,
        classify: Callable[[Point], Target],
        drag_start_px: float = DRAG_START_PX,
        click_max_seconds: float = CLICK_MAX_SECONDS,
        click_slop_px: float = CLICK_SLOP_PX,
    ) -> None:
        self._classify = classify
        self._drag_start_px = drag_start_px
        self._click_max_seconds = click_max_seconds
        self._click_slop_px = click_slop_px
        self._detector = PinchDetector()
        self._positions: deque[tuple[float, Point]] = deque()
        self._press: _Press | None = None

    @property
    def pinched(self) -> bool:
        return self._detector.pinched

    def update(self, t: float, pos: Point, value: float) -> list[GestureEvent]:
        """Feed one camera sample: its time, the (filtered) cursor position and pinch value."""
        self._positions.append((t, pos))
        while t - self._positions[0][0] > HISTORY_SECONDS + 0.2:
            self._positions.popleft()
        signal = self._detector.update(t, value)
        if signal == "press":
            onset = self._detector.closing_onset()
            lock = self._position_at(onset)
            target = self._classify(lock)
            self._press = _Press(target, lock, anchor=pos, onset=onset)
            return [GestureEvent("press", lock, target)]
        if signal == "release" and self._press is not None:
            return self._finish()
        if self._press is not None and self._detector.pinched:
            return self._hold(pos)
        return []

    def cancel(self) -> list[GestureEvent]:
        """Tracking was lost: forget the pinch in progress."""
        events = []
        if self._press is not None:
            events.append(GestureEvent("cancel", self._press.anchor, self._press.target))
        self._press = None
        self._detector.reset()
        self._positions.clear()
        return events

    def _hold(self, pos: Point) -> list[GestureEvent]:
        press = self._press
        if press is None or press.target[0] != "panel":
            return []
        events = []
        if not press.dragging and math.dist(pos, press.anchor) > self._drag_start_px:
            press.dragging = True
            events.append(GestureEvent("drag_start", press.anchor, press.target))
        if press.dragging:
            events.append(GestureEvent("drag", pos, press.target))
        return events

    def _finish(self) -> list[GestureEvent]:
        press, self._press = self._press, None
        open_at = self._detector.opening_onset()
        drop = self._position_at(open_at)  # where the cursor was before the fingers opened
        events = []
        if press.dragging:
            events.append(GestureEvent("drop", drop, press.target))
        elif (
            open_at - press.onset <= self._click_max_seconds
            and math.dist(drop, press.anchor) <= self._click_slop_px
        ):
            kind = press.target[0]
            if kind in ("button", "field"):
                events.append(GestureEvent("click", press.lock, press.target))
            elif kind == "panel":
                events.append(GestureEvent("tap", press.lock, press.target))
        events.append(GestureEvent("release", drop))
        return events

    def _position_at(self, t: float) -> Point:
        """The recorded cursor position closest in time to t."""
        return min(self._positions, key=lambda sample: abs(sample[0] - t))[1]
