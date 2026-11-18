"""Webcam hand tracking: a background thread that classifies your hand's pose (open/fist/other)
and tracks your index fingertip, writing both into a HandState the orb's frame timer polls. See
examples/phase7_step8_hand_gestures.py for the raw mechanism this wraps.
"""

import math
import threading
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

from jarvis.config import HAND_LANDMARKER_MODEL_PATH, HAND_LANDMARKER_MODEL_URL
from jarvis.vision.hand_state import HandState

WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_MCP = 9  # middle finger's knuckle - wrist-to-here is our "palm size" ruler
# Pinch = thumb tip close to index tip, measured in palm sizes so it works near or far from the
# camera. Two thresholds (hysteresis): start below PINCH_ON, end only above PINCH_OFF. With a
# single threshold, a gap hovering right at the line would flicker pinch/no-pinch every frame.
PINCH_ON = 0.30
PINCH_OFF = 0.45
# (MCP, PIP, TIP) for each non-thumb finger - used to tell "extended" from "curled".
FINGERS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}


def _ensure_model() -> None:
    if HAND_LANDMARKER_MODEL_PATH.exists():
        return
    HAND_LANDMARKER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, HAND_LANDMARKER_MODEL_PATH)


def _distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _is_extended(landmarks, mcp: int, pip: int, tip: int) -> bool:
    wrist = landmarks[WRIST]
    # A finger is "extended" if its tip is clearly farther from the wrist than its middle
    # joint is - works regardless of hand rotation, unlike comparing y-coordinates.
    return _distance(landmarks[tip], wrist) > _distance(landmarks[pip], wrist) * 1.1


def _classify_pose(landmarks) -> str:
    extended = sum(_is_extended(landmarks, *joints) for joints in FINGERS.values())
    if extended >= 3:
        return "open"
    if extended == 0:
        return "fist"
    return "other"


def pinch_ratio(landmarks) -> float:
    """Thumb-tip-to-index-tip gap divided by palm size (about 0.1 touching, 0.8+ wide open)."""
    palm = max(_distance(landmarks[WRIST], landmarks[MIDDLE_MCP]), 1e-6)
    return _distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm


def is_pinching(ratio: float, was_pinching: bool) -> bool:
    return ratio < (PINCH_OFF if was_pinching else PINCH_ON)


class HandTracker:
    """Runs entirely on its own thread - start()/stop() never touch the GUI thread, matching
    jarvis.voice.hotkey.Recorder's pattern for the microphone.
    """

    def __init__(self, state: HandState, camera_index: int = 0) -> None:
        self._state = state
        self._camera_index = camera_index
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self._state.set(None, "none")

    def _run(self) -> None:
        _ensure_model()
        options = mp_vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(HAND_LANDMARKER_MODEL_PATH)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        landmarker = mp_vision.HandLandmarker.create_from_options(options)
        capture = cv2.VideoCapture(self._camera_index)
        if not capture.isOpened():
            capture.release()
            landmarker.close()
            return  # no camera available - give up quietly rather than busy-looping forever
        start_time = time.monotonic()
        last_timestamp_ms = -1
        pinching = False
        try:
            while self._running:
                ok, frame = capture.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)  # mirror - feels natural, like a selfie camera
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                # detect_for_video demands a *strictly* increasing timestamp - two frames
                # processed within the same millisecond would otherwise crash it.
                timestamp_ms = max(
                    int((time.monotonic() - start_time) * 1000), last_timestamp_ms + 1
                )
                last_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                if result.hand_landmarks:
                    landmarks = result.hand_landmarks[0]
                    tip = landmarks[INDEX_TIP]
                    thumb = landmarks[THUMB_TIP]
                    pinching = is_pinching(pinch_ratio(landmarks), pinching)
                    midpoint = ((tip.x + thumb.x) / 2, (tip.y + thumb.y) / 2)
                    self._state.set((tip.x, tip.y), _classify_pose(landmarks), midpoint, pinching)
                else:
                    pinching = False
                    self._state.set(None, "none")
        finally:
            capture.release()
            landmarker.close()
