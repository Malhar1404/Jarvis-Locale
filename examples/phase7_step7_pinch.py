"""Phase 7: webcam pinch-to-zoom, the raw mechanism - no orb, no Qt, just a camera window so you
can SEE exactly what's being tracked. Bring your thumb and index finger together (a "pinch")
near the camera, then slowly spread them apart - the printed zoom number should climb above 1.0.
Bring them back together or open your hand fully to reset it to 1.0.

Downloads the hand-landmark model on first run (~7.8MB) into .data/models/.

Run with:  uv run python examples/phase7_step7_pinch.py
Press 'q' or close the window to quit.
"""

import math
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

from jarvis.config import HAND_LANDMARKER_MODEL_PATH, HAND_LANDMARKER_MODEL_URL

# Normalized distances (relative to the image, 0-1) - not true physical units, so these
# thresholds only work roughly at "hand a foot or two from the webcam" distances.
PINCH_START_DISTANCE = 0.045  # fingers must be at least this close to begin a pinch
PINCH_END_DISTANCE = 0.35  # fingers spread this far apart ends the gesture
ZOOM_MIN, ZOOM_MAX = 0.6, 1.8

THUMB_TIP = 4
INDEX_TIP = 8


def _ensure_model() -> None:
    if HAND_LANDMARKER_MODEL_PATH.exists():
        return
    HAND_LANDMARKER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading hand landmark model to {HAND_LANDMARKER_MODEL_PATH} (first run only)...")
    urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, HAND_LANDMARKER_MODEL_PATH)


_ensure_model()

options = mp_vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(HAND_LANDMARKER_MODEL_PATH)),
    running_mode=mp_vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)
landmarker = mp_vision.HandLandmarker.create_from_options(options)

capture = cv2.VideoCapture(0)
if not capture.isOpened():
    raise RuntimeError("Could not open the webcam (index 0).")

start_time = time.monotonic()
pinching = False
baseline_distance: float | None = None
zoom = 1.0
last_timestamp_ms = -1

print("Pinch (thumb + index close together), then spread them apart. 'q' to quit.")
try:
    while True:
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)  # mirror - feels natural, like a selfie camera
        height, width = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # detect_for_video demands a *strictly* increasing timestamp - two frames processed
        # within the same millisecond would otherwise send the same value twice and crash.
        timestamp_ms = max(int((time.monotonic() - start_time) * 1000), last_timestamp_ms + 1)
        last_timestamp_ms = timestamp_ms
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            thumb, index = landmarks[THUMB_TIP], landmarks[INDEX_TIP]
            distance = math.hypot(thumb.x - index.x, thumb.y - index.y)

            if not pinching and distance < PINCH_START_DISTANCE:
                pinching = True
                baseline_distance = distance
            elif pinching and distance > PINCH_END_DISTANCE:
                pinching = False
                baseline_distance = None

            zoom = max(ZOOM_MIN, min(ZOOM_MAX, distance / baseline_distance)) if pinching else 1.0

            thumb_px = (int(thumb.x * width), int(thumb.y * height))
            index_px = (int(index.x * width), int(index.y * height))
            cv2.circle(frame, thumb_px, 10, (0, 255, 255), -1)
            cv2.circle(frame, index_px, 10, (0, 255, 255), -1)
            cv2.line(frame, thumb_px, index_px, (0, 255, 255), 2)
            print(f"\rdistance={distance:.3f}  pinching={pinching}  zoom={zoom:.2f}  ", end="")
        else:
            pinching = False
            baseline_distance = None
            zoom = 1.0

        cv2.putText(
            frame,
            f"zoom: {zoom:.2f}" + ("  [PINCHING]" if pinching else ""),
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
        )
        cv2.imshow("Jarvis pinch test - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    capture.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("\nBye.")
