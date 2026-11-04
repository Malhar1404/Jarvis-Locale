"""Push-to-talk: hold a key to record from the microphone, release to get the clip back.

Two separate concerns live here on purpose: `Recorder` only knows about audio I/O (start/stop a
stream, hand back the samples); the key-listening in `listen_push_to_talk` only knows about
press/release events. Neither depends on the other's implementation.
"""

import numpy as np
import sounddevice as sd
from pynput import keyboard

from jarvis.config import SAMPLE_RATE


class Recorder:
    """Records mono float32 audio for as long as it's running, at config.SAMPLE_RATE."""

    def __init__(self) -> None:
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []

    def start(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._on_audio
        )
        self._stream.start()

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype="float32")
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(self._frames).flatten()


def listen_push_to_talk(key_name: str, on_start, on_stop) -> keyboard.Listener:
    """Calls on_start() when key_name is pressed and on_stop() when it's released. Returns the
    running listener (a thread) - call .join() to block, or .stop() to end it.
    """
    target = getattr(keyboard.Key, key_name, None) or keyboard.KeyCode.from_char(key_name)
    held = False

    def on_press(key: keyboard.Key) -> None:
        nonlocal held
        if key == target and not held:
            held = True
            on_start()

    def on_release(key: keyboard.Key) -> None:
        nonlocal held
        if key == target and held:
            held = False
            on_stop()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    return listener
