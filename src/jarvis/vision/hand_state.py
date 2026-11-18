"""A tiny shared value bridging the hand-tracking thread to the UI thread - the same pattern as
jarvis.voice.audio_level.AudioLevel: the tracking thread writes, the UI's own frame timer polls.
No lock needed for the same reason - a slightly stale read has no visible effect on an animation.
"""


class HandState:
    def __init__(self) -> None:
        self.pointer: tuple[float, float] | None = None  # index fingertip (x, y), or None
        self.pose: str = "none"  # "open", "fist", "other", or "none" (no hand detected)
        # Midpoint between thumb tip and index tip. The HUD cursor follows this instead of the
        # fingertip: when you pinch, the index tip moves toward the thumb, but the midpoint
        # stays put - so the cursor doesn't jump at the exact moment you "click".
        self.pinch_point: tuple[float, float] | None = None
        self.pinching: bool = False
        # When the camera frame behind these values was captured (time.monotonic()), and a counter
        # that goes up on every set(). The UI timer runs faster than the camera: the counter tells
        # it "this is a NEW sample" versus "the same one again", and the timestamp lets a filter
        # use the real gap between samples.
        self.timestamp: float | None = None
        self.seq = 0
        # Thumb-to-index gap in palm sizes (~1.0 open, <0.3 pinched): the raw signal the HUD's
        # PinchInteraction (vision/pinch.py) debounces itself. `pinching` above is the older,
        # already-thresholded version.
        self.pinch_value: float | None = None

    def set(
        self,
        pointer: tuple[float, float] | None,
        pose: str,
        pinch_point: tuple[float, float] | None = None,
        pinching: bool = False,
        timestamp: float | None = None,
        pinch_value: float | None = None,
    ) -> None:
        self.pointer = pointer
        self.pose = pose
        self.pinch_point = pinch_point
        self.pinching = pinching
        self.timestamp = timestamp
        self.pinch_value = pinch_value
        self.seq += 1  # last, so a reader that sees the new number also sees the new values
