"""Speech-to-text: loads the faster-whisper model once, so transcribe() is cheap to call
repeatedly. See examples/phase7_step1_stt.py for the raw mechanism this wraps.
"""

import numpy as np
from faster_whisper import WhisperModel

from jarvis.config import STT_COMPUTE_TYPE, STT_DEVICE, STT_MODEL

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE_TYPE)
    return _model


def transcribe(audio: np.ndarray) -> str:
    """audio: mono float32 samples at config.SAMPLE_RATE. vad_filter drops silence so Whisper
    doesn't hallucinate text during it (see phase-07 notes).
    """
    if audio.size == 0:
        return ""
    segments, _ = _get_model().transcribe(audio, language="en", vad_filter=True)
    return "".join(segment.text for segment in segments).strip()
