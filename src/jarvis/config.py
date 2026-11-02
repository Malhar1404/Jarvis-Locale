"""Central settings. Values can be overridden with JARVIS_* environment variables."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", PROJECT_ROOT / ".data"))

# qwen3:4b-instruct never thinks: fast and safe to speak aloud.
# (The plain qwen3:4b tag is the thinking-only variant. See docs/decisions/0002.)
MODEL = os.getenv("JARVIS_MODEL", "qwen3:4b-instruct")

# Only for models that can think (e.g. JARVIS_MODEL=qwen3:4b-thinking):
#   unset -> model default
#   "true" -> thoughts go to AIMessage.additional_kwargs["reasoning_content"]
_reasoning = os.getenv("JARVIS_REASONING")
REASONING: bool | None = None if _reasoning is None else _reasoning.lower() == "true"
