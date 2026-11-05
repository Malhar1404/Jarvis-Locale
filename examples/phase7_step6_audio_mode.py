"""Phase 7: "Audio mode" mechanism - continuous listening, no button to hold. Just talk, pause
when you're done, and the clip gets printed back as text. No agent, no TTS yet - this only
proves the live silence-detection mechanism (jarvis.voice.audio_mode.AudioModeListener) works
before wiring it into anything.

DEBUG BUILD: also saves each captured clip to .data/audio_mode_debug/ as a .wav and prints basic
stats, so a bad transcription can be told apart from a bad recording (play the .wav back and
listen - if it sounds clean and the text is still wrong, that's the model, not the segmenter).

Run with:  uv run python examples/phase7_step6_audio_mode.py
"""

import time
import wave

import numpy as np

from jarvis.config import DATA_DIR, SAMPLE_RATE
from jarvis.voice.audio_mode import AudioModeListener
from jarvis.voice.stt import transcribe

DEBUG_DIR = DATA_DIR / "audio_mode_debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
_clip_count = 0


def _save_wav(audio: np.ndarray, path) -> None:
    int16_audio = np.clip(audio * 32768.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(int16_audio.tobytes())


def on_utterance(audio: np.ndarray) -> None:
    global _clip_count
    _clip_count += 1
    duration = len(audio) / SAMPLE_RATE
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0

    wav_path = DEBUG_DIR / f"clip_{_clip_count:03d}.wav"
    _save_wav(audio, wav_path)

    print(f"\n[clip {_clip_count}] {duration:.2f}s  peak={peak:.3f}  rms={rms:.3f}")
    print(f"  saved: {wav_path}")

    text = transcribe(audio)
    if text:
        print(f"  You said: {text!r}")
    else:
        print("  (heard something, but no words came out of it)")


print("Audio mode running - just talk, then pause. Ctrl+C to quit.")
listener = AudioModeListener(on_utterance)
listener.start()
try:
    while True:
        time.sleep(0.2)
except KeyboardInterrupt:
    listener.stop()
    print("\nBye.")
