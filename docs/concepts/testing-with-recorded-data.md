# Testing and tuning with recorded data

**One line:** record real input once (numbers only), then replay it as often as you like to tune settings and prove behaviour - no raised arm needed.

## Why it exists
A camera, a hand and a Qt window are hard to test. Guessing settings ("beta = 0.02 looks about right")
gave us a cursor that barely smoothed. The recordings showed *why*: noise opened the filter.

## How it works
1. **Record** (`examples/phase7b_record_hand.py`): each camera frame becomes a `HandFrame`
   (time + 21 landmarks, or `None`). Saved as `.npz` in `.data/hand_recordings/` (gitignored).
   **No video, no images.** The script waits until your hand has been in view for 1 s, then counts down.
2. **Replay** (`examples/phase7b_tune_cursor.py`): push the frames through the filter and print
   *shake* (px of jitter) and *lag* (ms). Try other settings with `--min-cutoff` / `--beta`.
3. **Split the code** so most of it needs no Qt or camera:
   - pure logic (`pointer.py`, `pinch.py`) -> tested with made-up taps and drags that include the 30-50 px closing drift;
   - widget tests off-screen (`tests/ui/conftest.py`: `QT_QPA_PLATFORM=offscreen`) with a fake hand feeding 30 samples/s;
   - **replay on the real take** as the last check (4/4 quick taps clicked, 3/3 drags, no stray clicks).

## Lessons (from mistakes we made)
- **Check the data before trusting the number.** The scary "10 px shake" included 1.5 s with no hand in view.
- **A metric can lie.** Lag measured against *noisy* raw data always says 0 ms; compare against a lightly smoothed copy.
- **If a test fails, ask whether the test or the code is wrong.** Ours demanded < 2 px from +-8 px shake that was already 83% removed.
- **Few samples = few conclusions.** The first `click` take had only 2 taps; we asked for a re-record.

## Small example
```python
frames = load_recording(path)                      # list[HandFrame]
flt = OneEuroFilter2D(1.0, 0.004)
for f in frames:
    if f.landmarks is not None:
        x, y = map_to_screen(midpoint(f.landmarks), 1440, 900)
        cursor = flt(x, y, f.t)
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Tune live by hand | feels real | slow, tiring, not repeatable |
| Synthetic noise only | free, deterministic | not the shape of real camera noise (still used for unit tests) |
| Record video and re-run the model | tests the whole stack | privacy (images of you) and slow |
| Mock the camera class | simple unit tests | proves wiring, not the numbers |

## Related
- [[one-euro-filter]]
- [[pinch-click-vs-drag]]
- [[phase-07b-hud]]
