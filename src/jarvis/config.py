"""Central settings. Values can be overridden with JARVIS_* environment variables."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", PROJECT_ROOT / ".data"))
MODEL = os.getenv("JARVIS_MODEL", "qwen3:4b")
