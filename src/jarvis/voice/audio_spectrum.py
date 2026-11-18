"""AudioSpectrum: AudioLevel plus loudness per frequency band, for the arc reactor's wave ring.

An FFT (Fast Fourier Transform) turns a short slice of sound - a list of samples over time -
into "how much of each pitch is in it". A voice saying "ahh" shows energy at a low base pitch
plus its overtones; an "sss" shows energy high up. Grouping the FFT bins into bands gives one
number per wave-ring bar, so each bar follows a different part of Jarvis's real voice.

Same threading idea as AudioLevel: the audio thread writes `bands` (a fresh array each time, so
a reader never sees a half-written one), and the UI timer just reads the latest value.
"""

import numpy as np

from jarvis.voice.audio_level import AudioLevel

FFT_WINDOW = 1024  # samples per FFT (~46 ms at 22 kHz): enough pitch detail, still responsive
FLOOR_DB = -60.0  # quieter than this shows as an empty bar
CEIL_DB = -12.0  # louder than this shows as a full bar


def band_edges(band_count: int, low_hz: float, high_hz: float) -> np.ndarray:
    """Log-spaced edges: pitch is heard logarithmically (each octave doubles the frequency), so
    equal-width bands in Hz would give the top few bars almost all the range.
    """
    return np.geomspace(low_hz, high_hz, band_count + 1)


def band_levels(samples: np.ndarray, sample_rate: int, edges: np.ndarray) -> np.ndarray:
    """0..1 loudness per band for one slice of audio (a pure function, easy to test)."""
    window = np.hanning(len(samples))
    # Dividing by sum(window)/2 scales things so a full-volume sine wave reads as ~1.0.
    magnitudes = np.abs(np.fft.rfft(samples * window)) / (window.sum() / 2)
    freqs = np.fft.rfftfreq(len(samples), 1 / sample_rate)
    levels = np.empty(len(edges) - 1)
    for i in range(len(levels)):
        in_band = (freqs >= edges[i]) & (freqs < edges[i + 1])
        if in_band.any():
            levels[i] = magnitudes[in_band].max()
        else:  # a low band narrower than one FFT bin: use the bin nearest its centre
            centre = np.sqrt(edges[i] * edges[i + 1])
            levels[i] = magnitudes[np.argmin(np.abs(freqs - centre))]
    decibels = 20 * np.log10(levels + 1e-9)
    return np.clip((decibels - FLOOR_DB) / (CEIL_DB - FLOOR_DB), 0.0, 1.0)


class AudioSpectrum(AudioLevel):
    def __init__(self, band_count: int = 36, low_hz: float = 80.0, high_hz: float = 8000.0):
        super().__init__()
        self.band_count = band_count
        self.bands = np.zeros(band_count)
        self._low_hz = low_hz
        self._high_hz = high_hz
        self._buffer = np.zeros(FFT_WINDOW, dtype=np.float32)
        self._edges: dict[int, np.ndarray] = {}  # cached per sample rate

    def update(self, block: np.ndarray, sample_rate: int) -> None:
        super().update(block, sample_rate)  # keeps .value (overall loudness) working too
        n = len(block)
        if n == 0:
            return
        # Keep a rolling window of the most recent FFT_WINDOW samples. Audio blocks are often
        # smaller than that, and an FFT of a tiny block can't tell pitches apart.
        if n >= FFT_WINDOW:
            self._buffer = np.asarray(block[-FFT_WINDOW:], dtype=np.float32)
        else:
            self._buffer = np.concatenate([self._buffer[n:], block]).astype(np.float32)
        if sample_rate not in self._edges:
            self._edges[sample_rate] = band_edges(self.band_count, self._low_hz, self._high_hz)
        self.bands = band_levels(self._buffer, sample_rate, self._edges[sample_rate])

    def reset(self) -> None:
        super().reset()
        self._buffer = np.zeros(FFT_WINDOW, dtype=np.float32)
        self.bands = np.zeros(self.band_count)
