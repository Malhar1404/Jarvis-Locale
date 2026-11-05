"""A tiny shared value bridging the hand-tracking thread to the UI thread - the same pattern as
jarvis.voice.audio_level.AudioLevel: the tracking thread writes, the orb's own frame timer polls.
No lock needed for the same reason - a slightly stale read has no visible effect on an animation.
"""


class HandState:
    def __init__(self) -> None:
        self.pointer: tuple[float, float] | None = None  # index fingertip (x, y), or None
        self.pose: str = "none"  # "open", "fist", "other", or "none" (no hand detected)

    def set(self, pointer: tuple[float, float] | None, pose: str) -> None:
        self.pointer = pointer
        self.pose = pose
