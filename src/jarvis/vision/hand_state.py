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

    def set(
        self,
        pointer: tuple[float, float] | None,
        pose: str,
        pinch_point: tuple[float, float] | None = None,
        pinching: bool = False,
    ) -> None:
        self.pointer = pointer
        self.pose = pose
        self.pinch_point = pinch_point
        self.pinching = pinching
