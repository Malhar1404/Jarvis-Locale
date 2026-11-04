"""A tiny shared value bridging an audio thread (TTS playback or mic recording) to the UI
thread: the audio thread calls set() as each new block arrives, the orb's own frame timer reads
.value on the UI thread. A bare float attribute is enough here - CPython's GIL makes a single
assignment atomic, and a slightly stale read has zero visible effect on an animation, so there's
no need for a lock or a queued Qt signal per audio block (which, at ~50-100 blocks/second, would
be a lot of cross-thread traffic for no real benefit over just polling the latest value).
"""


class AudioLevel:
    def __init__(self) -> None:
        self.value = 0.0

    def set(self, value: float) -> None:
        self.value = max(0.0, min(1.0, value))
