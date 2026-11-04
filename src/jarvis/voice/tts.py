"""Text-to-speech: loads the Piper voice once, so speak() is cheap to call repeatedly. See
examples/phase7_step2_tts.py for the raw mechanism this wraps.
"""

import re
import threading

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from piper.download_voices import download_voice

from jarvis.config import TTS_VOICE, TTS_VOICES_DIR
from jarvis.voice.audio_level import AudioLevel

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


def speak(text: str, level: AudioLevel | None = None) -> None:
    """Synthesize text and play it, blocking until playback finishes. If level is given, its
    value is updated in real time as each audio block plays - so a UI widget (the orb) polling
    that value can react to the speech as it's actually heard, not just when it started.
    """
    if not text.strip():
        return
    chunks = list(_get_voice().synthesize(text))
    if not chunks:
        return
    audio = np.concatenate([chunk.audio_float_array for chunk in chunks])
    _play_with_level(audio, chunks[0].sample_rate, level)


def _play_with_level(audio: np.ndarray, sample_rate: int, level: AudioLevel | None) -> None:
    position = 0
    finished = threading.Event()

    def callback(outdata: np.ndarray, frames: int, time_info, status) -> None:
        nonlocal position
        chunk = audio[position : position + frames]
        outdata[: len(chunk), 0] = chunk
        if len(chunk) < frames:
            outdata[len(chunk) :, 0] = 0.0
        if level is not None:
            # RMS amplitude of this block, times a rough gain since speech RMS tends to sit low
            # (~0.05-0.2) in a [-1, 1] signal - this just maps it into a more visible 0..1 range.
            rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) else 0.0
            level.set(rms * 4)
        position += frames
        if position >= len(audio):
            finished.set()
            raise sd.CallbackStop

    with sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback):
        finished.wait()
    if level is not None:
        level.set(0.0)


class SentenceSpeaker:
    """Buffers streamed text and speaks it one completed sentence at a time, instead of waiting
    for an entire reply to finish generating before saying anything. The tradeoff: speak() is
    blocking, so playing a sentence pauses us from reading more of the stream for that long - but
    time-to-*first*-sound matters far more for how responsive this feels than total completion
    time, so that's the right tradeoff here.
    """

    def __init__(self, level: AudioLevel | None = None) -> None:
        self._buffer = ""
        self._level = level

    def feed(self, text: str) -> None:
        self._buffer += text
        *complete, self._buffer = _SENTENCE_BOUNDARY.split(self._buffer)
        for sentence in complete:
            speak(sentence, self._level)

    def flush(self) -> None:
        """Speak whatever's left (the final sentence has no trailing space to confirm it's
        done, so feed() always leaves it in the buffer until the reply ends).
        """
        if self._buffer.strip():
            speak(self._buffer, self._level)
        self._buffer = ""
