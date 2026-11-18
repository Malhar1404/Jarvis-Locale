import numpy as np

from jarvis.voice.audio_spectrum import FFT_WINDOW, AudioSpectrum, band_edges, band_levels

RATE = 22_050


def _sine(hz: float, n: int = FFT_WINDOW) -> np.ndarray:
    return np.sin(2 * np.pi * hz * np.arange(n) / RATE).astype(np.float32)


def test_silence_gives_empty_bands():
    levels = band_levels(np.zeros(FFT_WINDOW), RATE, band_edges(36, 80, 8000))
    assert levels.max() == 0.0


def test_a_tone_lights_up_its_own_band_most():
    edges = band_edges(36, 80, 8000)
    levels = band_levels(_sine(1000), RATE, edges)
    expected = int(np.searchsorted(edges, 1000) - 1)
    assert int(np.argmax(levels)) == expected
    assert levels[expected] > 0.9
    assert levels[0] < 0.5  # far-away bass band stays low


def test_spectrum_keeps_loudness_and_resets():
    spectrum = AudioSpectrum()
    spectrum.update(_sine(440, 512) * 0.5, RATE)
    assert spectrum.value > 0
    assert spectrum.bands.max() > 0
    spectrum.reset()
    assert spectrum.value == 0
    assert spectrum.bands.max() == 0
