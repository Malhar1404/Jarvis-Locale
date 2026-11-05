"""Central settings. Values can be overridden with JARVIS_* environment variables."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", PROJECT_ROOT / ".data"))

# Google Sheets (the timesheet tool). The key file lives in .data/ directly, NOT .data/workspace/,
# on purpose: workspace is readable by the file tools (list_files/read_file/search_files) - a
# credential must never sit somewhere the agent's own tools can read it.
GOOGLE_SERVICE_ACCOUNT_PATH = DATA_DIR / "google_service_account.json"
TIMESHEET_SPREADSHEET_ID = "1sX0qzAL9Pr4Xyx5WJDh5LiFAFSqKcpruec6KdqwDEes"
TIMESHEET_TAB_NAME = "Individual-Level"  # the only tab new entries are written to

# qwen3:4b-instruct never thinks: fast and safe to speak aloud.
# (The plain qwen3:4b tag is the thinking-only variant. See docs/decisions/0002.)
MODEL = os.getenv("JARVIS_MODEL", "qwen3:4b-instruct")

# Only for models that can think (e.g. JARVIS_MODEL=qwen3:4b-thinking):
#   unset -> model default
#   "true" -> thoughts go to AIMessage.additional_kwargs["reasoning_content"]
_reasoning = os.getenv("JARVIS_REASONING")
REASONING: bool | None = None if _reasoning is None else _reasoning.lower() == "true"

# Speech-to-text (faster-whisper, CPU). ".en" models are English-only and a bit faster/more
# accurate than the multilingual ones of the same size - fine since Jarvis only needs English.
STT_MODEL = os.getenv("JARVIS_STT_MODEL", "base.en")
STT_DEVICE = "cpu"
STT_COMPUTE_TYPE = "int8"  # faster-whisper's recommended quantization for CPU
SAMPLE_RATE = 16_000  # Hz - what Whisper expects on the way in

# Text-to-speech (Piper, CPU). Voice models are downloaded once (per voice) into .data/voices/.
TTS_VOICE = os.getenv("JARVIS_TTS_VOICE", "en_US-ryan-high")
TTS_VOICES_DIR = DATA_DIR / "voices"

# Hold this key to talk, release to stop recording. Must be a name pynput.keyboard.Key knows
# (e.g. "f9", "space") - see https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key
PUSH_TO_TALK_KEY = os.getenv("JARVIS_PUSH_TO_TALK_KEY", "f9")

# Webcam pinch-to-zoom (MediaPipe Hands). The model is downloaded once into .data/models/.
HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
HAND_LANDMARKER_MODEL_PATH = DATA_DIR / "models" / "hand_landmarker.task"
