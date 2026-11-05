"""Phase 7: hand-gesture mechanism, part A - fingertip tracking and open/fist pose
classification, no orb yet. Shows a camera window so you can see exactly what's detected:
- a dot on your index fingertip and on your palm center
- text showing your hand's classified pose (OPEN / FIST / OTHER)

Move your index finger around and watch the fingertip dot track it; make a fist, then open your
hand, and watch the pose label change. This proves both pieces hand-gestures will need before
either touches the orb.

Downloads the hand-landmark model on first run (~7.8MB) into .data/models/ (shared with the
earlier pinch experiment).

Run with:  uv run python examples/phase7_step8_hand_gestures.py
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

WRIST = 0
INDEX_TIP = 8
# (MCP, PIP, TIP) for each non-thumb finger - used to tell "extended" from "curled".
FINGERS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}
PALM_LANDMARKS = (0, 5, 9, 13, 17)  # wrist + all four MCP knuckles - used for a palm-center guess


def _ensure_model() -> None:
    if HAND_LANDMARKER_MODEL_PATH.exists():
        return
    HAND_LANDMARKER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading hand landmark model to {HAND_LANDMARKER_MODEL_PATH} (first run only)...")
    urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, HAND_LANDMARKER_MODEL_PATH)


def _distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _is_extended(landmarks, mcp: int, pip: int, tip: int) -> bool:
    wrist = landmarks[WRIST]
    # A finger is "extended" if its tip is clearly farther from the wrist than its middle
    # joint is - this works regardless of which way the hand is rotated, unlike comparing
    # y-coordinates (which silently assumes an upright hand).
    return _distance(landmarks[tip], wrist) > _distance(landmarks[pip], wrist) * 1.1


def classify_pose(landmarks) -> str:
    extended = sum(_is_extended(landmarks, *joints) for joints in FINGERS.values())
    if extended >= 3:
        return "OPEN"
    if extended == 0:
        return "FIST"
    return "OTHER"


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
last_timestamp_ms = -1

print("Move your index finger around; make a fist, then open your hand. 'q' to quit.")
try:
    while True:
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)  # mirror - feels natural, like a selfie camera
        height, width = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = max(int((time.monotonic() - start_time) * 1000), last_timestamp_ms + 1)
        last_timestamp_ms = timestamp_ms
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        pose = "NONE"
        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            pose = classify_pose(landmarks)

            palm_x = sum(landmarks[i].x for i in PALM_LANDMARKS) / len(PALM_LANDMARKS)
            palm_y = sum(landmarks[i].y for i in PALM_LANDMARKS) / len(PALM_LANDMARKS)
            tip = landmarks[INDEX_TIP]

            tip_px = (int(tip.x * width), int(tip.y * height))
            palm_px = (int(palm_x * width), int(palm_y * height))
            cv2.circle(frame, tip_px, 12, (0, 255, 255), -1)
            cv2.circle(frame, palm_px, 8, (255, 0, 255), -1)
            cv2.line(frame, palm_px, tip_px, (0, 255, 255), 2)
            print(f"\rpose={pose:6s}  fingertip=({tip.x:.2f}, {tip.y:.2f})  ", end="")

        color = {"OPEN": (0, 255, 0), "FIST": (0, 0, 255), "OTHER": (0, 165, 255)}.get(
            pose, (128, 128, 128)
        )
        cv2.putText(frame, pose, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2)
        cv2.imshow("Jarvis hand-gesture test - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    capture.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("\nBye.")
