# Phase 7: Voice

**Status:** done (barge-in and a wake word deferred - see Next)
**Date:** 2026-11-05

## Goal
Run an everyday task entirely by voice, including a spoken reply - and, along the way, a real
visual centerpiece for the UI the user had been wanting since Phase 6: a hand-gesture-controlled
voice orb.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | Speech-to-text mechanism: record a clip, transcribe with `faster-whisper` (CPU). Found and fixed Whisper hallucinating on silence with `vad_filter=True` | `examples/phase7_step1_stt.py`, `jarvis/voice/stt.py` |
| 2 | Text-to-speech mechanism: Piper synthesizes text, `sounddevice` plays it. Voice set to `en_US-ryan-high` for a deeper, more "movie Jarvis" sound | `examples/phase7_step2_tts.py`, `jarvis/voice/tts.py` |
| 3 | The full voice loop, no UI yet: push-to-talk (`pynput`), record, transcribe, run through the `Agent`, speak the reply | `examples/phase7_step3_voice_loop.py`, `jarvis/voice/hotkey.py` |
| - | Streaming TTS: speak each sentence as it completes instead of waiting for the whole reply - fixed a real "Jarvis is laggy" complaint | `jarvis/voice/tts.py`'s `SentenceSpeaker` |
| - | A hands-free "Audio mode" (continuous listening via live `webrtcvad` silence detection) was built and its segmentation logic verified correct, but real transcriptions came back wrong. Parked, not wired into the app | `jarvis/voice/audio_mode.py` |
| 4 | Wired voice into the Qt UI: a push-to-talk mic button (review before sending) and a global hotkey (auto-send + spoken reply) - two different tools for two different moments | `src/jarvis/ui/main_window.py`, `src/jarvis/ui/worker.py` |
| 5 | The voice orb: a rotating dotted sphere (`QPainter`, no 3D engine) that deforms with Jarvis's own speech volume, click-to-expand fullscreen | `src/jarvis/ui/orb.py` |
| 6 | Webcam hand gestures controlling the orb (replacing an unsatisfying pinch-to-zoom attempt): move your index finger to move and squash the orb, close/open your fist to squeeze then burst it outward | `src/jarvis/vision/` |

## Concepts learned
- [[voice-activity-detection]]
- Reused from Phase 6: [[qt-threading]] (every audio/vision background thread uses the same "thread writes, UI polls" shape as `AudioLevel`)

## How it works (my own words)
_Write this yourself. Pick one real bug from "Things we noticed" below and explain, as if telling
a friend, what actually went wrong and why the fix worked - not just what the fix was._

## Things we noticed (real findings, not theory)
- **Whisper hallucinates on silence** - a fixed-length recording with trailing silence came back
  with invented extra sentences. Fixed with `vad_filter=True`. See [[voice-activity-detection]].
- **A hands-free "Audio mode" looked right but wasn't.** The live-silence-detection state machine
  was provably correct (verified with a scripted test), yet real transcriptions came back
  coherent-sounding but wrong. Rather than chase it further, push-to-talk was built instead - the
  key itself is a perfect start/end signal, sidestepping the problem.
- **A real concurrency bug, caused by Phase 6's own tray feature.** Pressing the push-to-talk
  hotkey spoke the reply twice, simultaneously. Not a code bug: since closing a window now hides
  it to the tray instead of quitting, several test launches had stacked up as separate live
  processes, each with its own hotkey listener and TTS pipeline. Fixed by closing the stale
  processes - a reminder that "it's running" and "there's exactly one of it running" are
  different claims.
- **"It should only react to Jarvis, not me."** The orb's first wiring shared one `AudioLevel`
  between the microphone and Jarvis's TTS, so it pulsed with *your* voice too. The fix was
  structural, not a tuning tweak: the `Recorder` stopped sharing the level at all.
- **Pinch-to-zoom didn't feel right, even though the math worked.** The gesture was replaced
  outright with finger-follow + fist-squeeze/burst, which needed real new capability: classifying
  the *whole hand's pose* (open/fist), not just a distance between two points, and giving each
  point in the orb its own transient, decaying state (a tiny damped spring) - everything before
  this was a pure function of time and audio level, with no memory at all.
- **`ruff` caught a real bug while writing the burst effect**: `pz` was built from `spun_z`
  instead of `tilted_z`, silently dropping the tilt transform from the depth sort. `F841`
  ("unused variable") flagged `tilted_z` as dead code - which it only was *because* of the bug.

## What confused me / questions I still have
-

## Code to look at
- `jarvis/voice/stt.py` / `tts.py`: small, load-once wrappers - compare to the raw mechanism in
  `examples/phase7_step1_stt.py` / `step2_tts.py`.
- `jarvis/ui/orb.py`: `_tick_hand()` - the whole finger-follow/squeeze/burst state machine in
  about 30 lines, each piece a simple exponential-smoothing or damped-spring update.
- `jarvis/vision/hand_tracking.py`: compare its shape to `jarvis/voice/hotkey.py`'s `Recorder` -
  same "runs on its own thread, writes a shared value, never touches a widget" pattern, one for
  a webcam instead of a microphone.

## Next
[[PLAN]] Barge-in (interrupting Jarvis mid-sentence) and an optional wake word were on Phase 7's
original concept list but aren't required by its "done when" bar - deferred as follow-ups,
pickable up whenever wanted. The parked "Audio mode" could also be revisited later. Next phase:
[[PLAN]] Phase 8, memory and context.
