"""Phase 7, step 2: text-to-speech, the raw mechanism - text in, speech out, no agent yet.

Downloads a Piper voice model on first run (~60MB) into .data/voices/, synthesizes a sentence,
and plays it back through your speakers with sounddevice.

Run with:  uv run python examples/phase7_step2_tts.py
"""

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from piper.download_voices import download_voice

from jarvis.config import TTS_VOICE, TTS_VOICES_DIR

TTS_VOICES_DIR.mkdir(parents=True, exist_ok=True)
model_path = TTS_VOICES_DIR / f"{TTS_VOICE}.onnx"

if not model_path.exists():
    print(f"Downloading voice '{TTS_VOICE}' to {TTS_VOICES_DIR} (first run only)...")
    download_voice(TTS_VOICE, TTS_VOICES_DIR)

print(f"Loading voice '{TTS_VOICE}'...")
voice = PiperVoice.load(model_path)

text = "Hello! I am Jarvis, your local voice assistant, running entirely on your own PC."
print(f"\nSynthesizing: {text!r}")

# synthesize() yields the audio in chunks (useful later for streaming) - for this mechanism
# test we just collect all of them and play the whole thing at once.
chunks = list(voice.synthesize(text))
audio = np.concatenate([chunk.audio_float_array for chunk in chunks])
sample_rate = chunks[0].sample_rate

print(f"Got {len(chunks)} audio chunk(s), {len(audio) / sample_rate:.2f}s total. Playing...")
sd.play(audio, samplerate=sample_rate)
sd.wait()
print("Done.")
