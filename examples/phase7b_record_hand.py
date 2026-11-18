"""Phase 7b: record a hand-tracking session so the cursor can be tuned on YOUR hand.

What is saved: only numbers - for every camera frame, a timestamp and the 21 landmark points
MediaPipe found. No video, no images. It goes to .data/hand_recordings/<name>.npz on this PC
(.data/ is gitignored) and you can delete it any time. The webcam light will be on while this runs.

Make one take per name (each ~10 s, after a 3 s countdown):
    uv run python examples/phase7b_record_hand.py still
    uv run python examples/phase7b_record_hand.py click
    uv run python examples/phase7b_record_hand.py drag
    uv run python examples/phase7b_record_hand.py move
Sit and hold your hand the way you normally would when using interactive mode.
"""

import argparse
import threading
import time

from jarvis.config import HAND_RECORDINGS_DIR
from jarvis.vision.hand_recording import HandFrame, save_recording
from jarvis.vision.hand_state import HandState
from jarvis.vision.hand_tracking import HandTracker

INSTRUCTIONS = {
    "still": (
        "First half: hold your hand up as if aiming at the screen, fingers apart, and keep it\n"
        "as STILL as you can (just try to hold it steady).\n"
        "Second half: pinch thumb and index finger together and hold that, again as still as\n"
        "you can."
    ),
    "click": (
        "Aim at an imaginary button and keep your hand there. TAP-pinch (pinch and release\n"
        "quickly) about once a second, around 8 times. Try not to move your hand on purpose."
    ),
    "drag": (
        "Pinch, then keep the pinch and move your hand slowly to the right; release.\n"
        "Move back, pinch again, drag slowly left; release. Repeat 3 or 4 times."
    ),
    "move": (
        "Without pinching: move your hand slowly across the whole 'screen' - left, right, up,\n"
        "down - then do a few quick flicks from one side to the other."
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Record hand landmarks (numbers only).")
    parser.add_argument("name", help="name of the take, e.g. still / click / drag / move")
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()

    frames: list[HandFrame] = []
    recording = threading.Event()
    first_frame = threading.Event()
    seen_since: list[float | None] = [None]  # when the hand last (re)appeared; None = not seen

    def on_frame(frame: HandFrame) -> None:  # runs on the tracker's thread
        first_frame.set()
        if frame.landmarks is None:
            seen_since[0] = None
        elif seen_since[0] is None:
            seen_since[0] = frame.t
        if recording.is_set():
            frames.append(frame)

    tracker = HandTracker(HandState(), on_frame=on_frame)
    print("Starting the camera (the first start loads the model, a few seconds)...")
    tracker.start()
    try:
        if not first_frame.wait(timeout=30):
            print("No frames from the camera. Is it connected and not used by another app?")
            return
        steps = INSTRUCTIONS.get(args.name, "Do whatever you want to test.")
        print(f"\nTake '{args.name}':\n{steps}\n")
        print("Hold your hand up in view now. The countdown starts once I have seen it for 1 s.")
        deadline = time.monotonic() + 60
        while seen_since[0] is None or time.monotonic() - seen_since[0] < 1.0:
            if time.monotonic() > deadline:
                print("I never saw a hand. Check the lighting and that your hand is in view.")
                return
            time.sleep(0.05)
        for count in (3, 2, 1):
            print(f"  {count}...")
            time.sleep(1)
        print(f"  RECORDING for {args.seconds:.0f} s - go!")
        recording.set()
        time.sleep(args.seconds)
        recording.clear()
        print("  done.")
    finally:
        tracker.stop()

    if not frames:
        print("Nothing was recorded.")
        return
    path = HAND_RECORDINGS_DIR / f"{args.name}.npz"
    save_recording(path, frames)

    seen = [f for f in frames if f.landmarks is not None]
    span = frames[-1].t - frames[0].t
    print(f"\nSaved {len(frames)} frames to {path}")
    print(f"  camera rate:   {len(frames) / span:.1f} frames/s" if span > 0 else "")
    print(f"  hand detected: {100 * len(seen) / len(frames):.0f}% of frames")
    if len(seen) < 0.8 * len(frames):
        print("  (low - check the lighting, and that your whole hand is in view)")


if __name__ == "__main__":
    main()
