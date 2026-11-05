""" "Audio mode": hands-free, continuous listening - no button to hold per turn. Segments speech
out of a live mic stream using webrtcvad (frame-by-frame speech/non-speech classification) and
calls on_utterance(audio) once a silence gap confirms you're done talking.

This is a different problem from jarvis.voice.stt's vad_filter: that one cleans up a clip we
already finished recording (after the fact). This has to decide, live, while audio keeps
arriving, when an utterance has actually ended - webrtcvad doesn't do that cleanup step itself,
so the state machine below (buffer -> trigger -> track silence -> cut) is ours.
"""

import collections
from collections.abc import Callable

import numpy as np
import sounddevice as sd
import webrtcvad

from jarvis.config import SAMPLE_RATE
from jarvis.voice.audio_level import AudioLevel

FRAME_MS = 30  # webrtcvad only accepts 10, 20, or 30ms frames
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000
PADDING_MS = 300  # audio kept from just before speech is detected, so the first word isn't cut
PADDING_FRAMES = PADDING_MS // FRAME_MS
SILENCE_MS = 800  # how long a gap must be before an utterance is considered finished
SILENCE_FRAMES = SILENCE_MS // FRAME_MS
VAD_AGGRESSIVENESS = 2  # 0 (permissive) - 3 (strict about what counts as speech)


class AudioModeListener:
    """Runs entirely inside sounddevice's own audio thread (via its InputStream callback) - no
    extra thread of our own needed, the same pattern jarvis.voice.hotkey.Recorder already uses.
    on_utterance and level updates therefore happen on that audio thread, not the caller's.
    """

    def __init__(
        self,
        on_utterance: Callable[[np.ndarray], None],
        level: AudioLevel | None = None,
    ) -> None:
        self._on_utterance = on_utterance
        self._level = level
        self._vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self._stream: sd.InputStream | None = None

        self._ring_buffer: collections.deque[tuple[np.ndarray, bool]] = collections.deque(
            maxlen=PADDING_FRAMES
        )
        self._triggered = False
        self._voiced_frames: list[np.ndarray] = []
        self._silence_run = 0

    def start(self) -> None:
        if self._stream is not None:
            return
        self._ring_buffer.clear()
        self._triggered = False
        self._voiced_frames = []
        self._silence_run = 0
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if self._level is not None:
            self._level.set(0.0)

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if frames != FRAME_SAMPLES:
            return  # a short final block from the driver - not a full 30ms frame, skip it
        frame = indata[:, 0].copy()
        is_speech = self._vad.is_speech(frame.tobytes(), SAMPLE_RATE)

        if self._level is not None:
            rms = float(np.sqrt(np.mean((frame.astype(np.float32) / 32768.0) ** 2)))
            self._level.set(rms * 6)

        if not self._triggered:
            self._ring_buffer.append((frame, is_speech))
            voiced_ratio = sum(speech for _, speech in self._ring_buffer) / max(
                1, len(self._ring_buffer)
            )
            if len(self._ring_buffer) == PADDING_FRAMES and voiced_ratio > 0.6:
                self._triggered = True
                self._voiced_frames = [f for f, _ in self._ring_buffer]
                self._ring_buffer.clear()
                self._silence_run = 0
        else:
            self._voiced_frames.append(frame)
            if is_speech:
                self._silence_run = 0
            else:
                self._silence_run += 1
                if self._silence_run >= SILENCE_FRAMES:
                    self._finish_utterance()

    def _finish_utterance(self) -> None:
        audio_int16 = np.concatenate(self._voiced_frames)
        audio = audio_int16.astype(np.float32) / 32768.0
        self._triggered = False
        self._voiced_frames = []
        self._ring_buffer.clear()
        self._silence_run = 0
        if self._level is not None:
            self._level.set(0.0)
        self._on_utterance(audio)
