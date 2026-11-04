"""Text-to-speech: loads the Piper voice once, so speak() is cheap to call repeatedly. See
examples/phase7_step2_tts.py for the raw mechanism this wraps.
"""

import re

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from piper.download_voices import download_voice

from jarvis.config import TTS_VOICE, TTS_VOICES_DIR

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

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


class SentenceSpeaker:
    """Buffers streamed text and speaks it one completed sentence at a time, instead of waiting
    for an entire reply to finish generating before saying anything. The tradeoff: speak() is
    blocking, so playing a sentence pauses us from reading more of the stream for that long - but
    time-to-*first*-sound matters far more for how responsive this feels than total completion
    time, so that's the right tradeoff here.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, text: str) -> None:
        self._buffer += text
        *complete, self._buffer = _SENTENCE_BOUNDARY.split(self._buffer)
        for sentence in complete:
            speak(sentence)

    def flush(self) -> None:
        """Speak whatever's left (the final sentence has no trailing space to confirm it's
        done, so feed() always leaves it in the buffer until the reply ends).
        """
        if self._buffer.strip():
            speak(self._buffer)
        self._buffer = ""
