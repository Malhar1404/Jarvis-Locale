# Voice activity detection (VAD)

**One line:** telling which parts of an audio stream are actually speech - needed in two very
different situations: cleaning up a clip you've already finished recording, versus deciding,
live, that someone just stopped talking.

## Why it exists
Whisper (and faster-whisper) will happily generate text for silence - it has no built-in
"there's nothing here" signal, so given a few seconds of near-silence it sometimes hallucinates
plausible-sounding sentences nobody said. We hit this directly in Phase 7 step 1: a 5-second
fixed-length recording came back as `"Hey, what you doing, mate? I'm clean. Well, yeah, I'm
clean."` - only the first sentence was real; the rest was the model filling silence with
invented words. A continuous, hands-free "just talk, no button" mode has a second, harder
problem: it has to decide *live*, frame by frame, when you've stopped talking, with no "you're
done recording" signal at all (unlike push-to-talk, where releasing the key tells you exactly
when the clip ends).

## How it works
Two different tools for the two different problems, both working on this project:

**Post-hoc (cleaning up a finished clip):** `faster-whisper`'s `transcribe(audio, vad_filter=True)`
runs Silero VAD (via `onnxruntime`, already a transitive dependency) over the whole clip first and
only feeds Whisper the parts it thinks are speech. One flag, no state to manage - this is what
fixed the hallucination bug in `jarvis/voice/stt.py`.

**Live (deciding when an utterance has ended):** `webrtcvad` classifies one small, fixed-size
audio frame (10/20/30ms) at a time as speech or not - it has no concept of "silence long enough
to be done," so that logic has to be built on top, in `jarvis/voice/audio_mode.py`:
```
not triggered:  keep the last ~300ms of frames in a ring buffer (so the first word isn't
                clipped); if >60% of them are speech, trigger - start the real recording
triggered:      keep appending frames; count consecutive non-speech frames; once that run
                is long enough (800ms), the utterance is finished - cut it and reset
```
This state machine was verified correct with a scripted speech/silence sequence - it triggers,
pads, waits through silence, and cuts exactly once. But real transcriptions still came back
coherent-sounding yet wrong ("completely off," per testing) - segmentation alone wasn't enough
to fix it, and the cause wasn't tracked down further. **Parked, not solved**: the code and a
debug demo that dumps each captured clip to a `.wav` (`examples/phase7_step6_audio_mode.py`) are
kept for a possible later look, but nothing from it is wired into the app. The global
push-to-talk hotkey was built instead - the key press/release already *is* a perfect start/end
signal, which sidesteps the live-detection problem entirely.

## Alternatives
| Option | Good for | Why / why not |
|---|---|---|
| `faster-whisper`'s `vad_filter=True` (using this, post-hoc) | Cleaning a clip you already have in full | - |
| `webrtcvad` (using this, live) | Frame-by-frame speech/silence classification, tiny and fast | Needs a hand-built state machine on top to turn "is this frame speech" into "has the utterance ended" |
| Push-to-talk instead of live VAD (what we shipped) | A perfect, free end-of-utterance signal | Not hands-free - you have to hold a key |
| Silero VAD's own streaming API directly | No new dependency (already have `onnxruntime`) | Its public interface is built for post-hoc filtering, not live frame-by-frame decisions - fighting the library |
| Plain RMS energy threshold | Zero dependencies | Can't tell speech from a cough, chair creak, or background hum as reliably as something trained for it |

## Related
- [[qt-threading]] - how a live VAD's background audio thread would hand a finished clip back to the UI thread
- `jarvis/voice/audio_level.py`'s `AudioLevel` - the same "background thread writes, UI polls" shape, for a different signal (volume, not speech/silence)
