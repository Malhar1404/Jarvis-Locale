# FFT audio spectrum (the sound-wave ring)

**One line:** an FFT turns a short slice of sound into "how much of each pitch is in it", so each bar can follow a different pitch.

## Why it exists
Loudness (RMS) is one number: every bar would move the same way. A voice has low hum and high "sss";
bars that follow *different pitch bands* look like a real equalizer.

## How it works (`voice/audio_spectrum.py`)
1. Keep a **rolling window** of the last 1024 samples (audio blocks are often smaller, and a tiny
   block can't tell pitches apart).
2. Multiply by a **Hann window** (fades the edges so the cut doesn't create fake frequencies).
3. `np.fft.rfft` -> magnitude per frequency.
4. Group frequencies into **36 log-spaced bands** from 80 Hz to 8 kHz. Pitch is heard in octaves
   (each doubles the frequency), so equal-width bands in Hz would give the top bars nearly all the range.
5. Convert to **decibels** and map -60 dB..-12 dB to 0..1 (quiet = empty bar, loud = full bar).
6. The reactor **mirrors** the 36 bands left/right (72 bars) and smooths: fast up, slow down.

Threading: the audio thread writes `bands` (a fresh array each time, never half-written); the UI
timer just reads the latest. Same "thread writes, UI polls" pattern as `AudioLevel`.
TTS playback now calls `level.update(chunk, sample_rate)` and `level.reset()` at the end.

## Small example
```python
edges = band_edges(36, 80, 8000)
levels = band_levels(tone_1000hz, 22050, edges)   # the band holding 1000 Hz is ~1.0, bass band ~0
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| RMS loudness only | simplest; the old orb used it | all bars move together |
| Random animation | looks busy with zero work | not reactive to the voice (you asked for reactive) |
| Linear-spaced bands | simple maths | top bars would get almost all the range |
| Spectrogram / mel bands | speech analysis | more than a ring of bars needs |
| Reading the mic | visualises *your* voice | you wanted it to follow Jarvis only |

## Related
- [[qt-threading]]
- [[phase-07b-hud]]
