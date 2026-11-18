"""Phase 7b: replay recorded hands through the cursor filter and report how steady it is.

No camera needed. For each recording in .data/hand_recordings/ it builds the cursor path two
ways - raw (what the unfiltered hand position would do) and filtered - and prints:
    shake    how many screen pixels of high-frequency jitter the path has (lower = steadier)
    lag      how far the filtered path trails the raw one (only meaningful for moving takes)
Use --min-cutoff / --beta to try other settings without touching the app.

Run: uv run python examples/phase7b_tune_cursor.py
     uv run python examples/phase7b_tune_cursor.py --min-cutoff 0.6 --beta 0.03
"""

import argparse

import numpy as np

from jarvis.config import HAND_RECORDINGS_DIR
from jarvis.ui.hud.gestures import (
    ACTIVE_HIGH,
    ACTIVE_LOW,
    FILTER_BETA,
    FILTER_D_CUTOFF,
    FILTER_MIN_CUTOFF,
)
from jarvis.vision.hand_recording import HandFrame, load_recording
from jarvis.vision.hand_tracking import INDEX_TIP, THUMB_TIP
from jarvis.vision.pointer import OneEuroFilter2D, map_to_screen

SCREEN = (1440, 900)


def cursor_paths(frames: list[HandFrame], filt: OneEuroFilter2D):
    """Return (times, raw_xy, filtered_xy) for the frames where a hand was seen."""
    times, raw, out = [], [], []
    for frame in frames:
        if frame.landmarks is None:
            continue
        # The same point the app follows: halfway between thumb tip and index tip.
        mid = (frame.landmarks[THUMB_TIP, :2] + frame.landmarks[INDEX_TIP, :2]) / 2
        x, y = map_to_screen((mid[0], mid[1]), *SCREEN, ACTIVE_LOW, ACTIVE_HIGH)
        times.append(frame.t)
        raw.append((x, y))
        out.append(filt(x, y, frame.t))
    return np.array(times), np.array(raw), np.array(out)


def shake_px(path: np.ndarray) -> float:
    """Jitter estimate: how far each point sits from the middle of its two neighbours. Smooth
    motion scores ~0; random noise of size s scores ~s (the 1.5 undoes the averaging).
    """
    if len(path) < 3:
        return 0.0
    residual = path[1:-1] - (path[:-2] + path[2:]) / 2
    return float(np.sqrt(np.mean(np.sum(residual**2, axis=1)) / 1.5))


def lag_ms(times: np.ndarray, raw: np.ndarray, filtered: np.ndarray) -> float:
    """How far the filtered path trails the hand, in ms.

    Comparing against the raw path directly would be misleading: its noise makes "no shift" look
    best. So the reference is the raw path averaged over 5 frames, centred (a zero-lag smooth).
    """
    kernel = np.ones(5) / 5
    reference = np.column_stack([np.convolve(raw[:, axis], kernel, mode="same") for axis in (0, 1)])
    edge = 4  # skip the first/last frames, where the centred average is incomplete
    best, best_error = 0, float("inf")
    for shift in range(0, 12):
        a = filtered[edge + shift : len(raw) - edge]
        b = reference[edge : len(raw) - edge - shift]
        error = np.mean(np.abs(a - b))
        if error < best_error:
            best, best_error = shift, error
    return best * float(np.median(np.diff(times))) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-cutoff", type=float, default=FILTER_MIN_CUTOFF)
    parser.add_argument("--beta", type=float, default=FILTER_BETA)
    args = parser.parse_args()
    files = sorted(HAND_RECORDINGS_DIR.glob("*.npz"))
    if not files:
        print(f"No recordings in {HAND_RECORDINGS_DIR}. Run phase7b_record_hand.py first.")
        return
    print(f"filter: min_cutoff={args.min_cutoff}  beta={args.beta}  screen={SCREEN}\n")
    print(f"{'take':<10}{'frames':>7}{'shake raw':>11}{'shake filt':>12}{'reduced':>9}{'lag':>9}")
    for path in files:
        frames = load_recording(path)
        filt = OneEuroFilter2D(args.min_cutoff, args.beta, FILTER_D_CUTOFF)
        times, raw, out = cursor_paths(frames, filt)
        if len(times) < 5:
            print(f"{path.stem:<10}{len(frames):>7}  (hand barely detected)")
            continue
        s_raw, s_out = shake_px(raw), shake_px(out)
        reduced = f"{100 * (1 - s_out / s_raw):.0f}%" if s_raw else "-"
        print(
            f"{path.stem:<10}{len(frames):>7}{s_raw:>9.1f}px{s_out:>10.1f}px{reduced:>9}"
            f"{lag_ms(times, raw, out):>7.0f}ms"
        )


if __name__ == "__main__":
    main()
