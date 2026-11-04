"""Text-to-speech: loads the Piper voice once, so speak() is cheap to call repeatedly. See
examples/phase7_step2_tts.py for the raw mechanism this wraps.
"""

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from piper.download_voices import download_voice

from jarvis.config import TTS_VOICE, TTS_VOICES_DIR

_voice: PiperVoice | None = None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        TTS_VOICES_DIR.mkdir(parents=True, exist_ok=True)
        model_path = TTS_VOICES_DIR / f"{TTS_VOICE}.onnx"
        if not model_path.exists():
            download_voice(TTS_VOICE, TTS_VOICES_DIR)
        _voice = PiperVoice.load(model_path)
    return _voice


def speak(text: str) -> None:
    """Synthesize text and play it, blocking until playback finishes."""
    if not text.strip():
        return
    chunks = list(_get_voice().synthesize(text))
    if not chunks:
        return
    audio = np.concatenate([chunk.audio_float_array for chunk in chunks])
    sd.play(audio, samplerate=chunks[0].sample_rate)
    sd.wait()
