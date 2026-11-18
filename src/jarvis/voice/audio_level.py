"""A tiny shared value bridging an audio thread (TTS playback or mic recording) to the UI
thread: the audio thread calls set() as each new block arrives, the orb's own frame timer reads
.value on the UI thread. A bare float attribute is enough here - CPython's GIL makes a single
assignment atomic, and a slightly stale read has zero visible effect on an animation, so there's
no need for a lock or a queued Qt signal per audio block (which, at ~50-100 blocks/second, would
be a lot of cross-thread traffic for no real benefit over just polling the latest value).

update(block, sample_rate) is what TTS playback calls per block; AudioSpectrum (see
audio_spectrum.py) overrides it to also compute frequency bands for the arc reactor.
"""

import numpy as np


class AudioLevel:
    def __init__(self) -> None:
        self.value = 0.0

    def set(self, value: float) -> None:
        self.value = max(0.0, min(1.0, value))

    def update(self, block: np.ndarray, sample_rate: int) -> None:  # noqa: ARG002
        """Called by the audio thread for every block it plays."""
        # RMS amplitude of this block, times a rough gain since speech RMS tends to sit low
        # (~0.05-0.2) in a [-1, 1] signal - this just maps it into a more visible 0..1 range.
        rms = float(np.sqrt(np.mean(block**2))) if len(block) else 0.0
        self.set(rms * 4)

    def reset(self) -> None:
        """Playback finished - go back to silence."""
        self.set(0.0)
