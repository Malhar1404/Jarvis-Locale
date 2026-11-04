"""Phase 7, step 1: speech-to-text, the raw mechanism - no hotkey, no agent, no VAD yet.

Records a fixed few seconds from your microphone, then transcribes it with faster-whisper
running on CPU. The first run downloads the model from Hugging Face (~140MB for base.en) and
caches it; later runs are instant to load.

Run with:  uv run python examples/phase7_step1_stt.py
"""

import time

import sounddevice as sd
from faster_whisper import WhisperModel

from jarvis.config import SAMPLE_RATE, STT_COMPUTE_TYPE, STT_DEVICE, STT_MODEL

DURATION_SECONDS = 5

print(f"Loading faster-whisper model '{STT_MODEL}' ({STT_DEVICE}, {STT_COMPUTE_TYPE})...")
model = WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE_TYPE)

print(f"\nRecording for {DURATION_SECONDS} seconds - speak now!")
recording = sd.rec(
    int(DURATION_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32"
)
sd.wait()
audio = recording.flatten()
print("Done recording.")

print("\nTranscribing...")
start = time.perf_counter()
# vad_filter=True runs Silero VAD first and only feeds Whisper the parts that are actually
# speech - without it, Whisper tends to hallucinate text during the trailing silence.
segments, info = model.transcribe(audio, language="en", vad_filter=True)
text = "".join(segment.text for segment in segments).strip()
elapsed = time.perf_counter() - start

print(f"\nDetected language: {info.language} (p={info.language_probability:.2f})")
print(f"Transcribed in {elapsed:.2f}s")
print(f"\nYou said: {text!r}")
