# Phase 7b: The HUD (floating panels, arc reactor, hand cursor)

**Status:** in progress (built and committed; waiting for the live hand test and the hover feedback)
**Date:** 2026-11-18

## Goal
Replace the plain chat window with an Iron-Man style screen: one dark full-screen window, an arc
reactor in the middle that reacts to Jarvis's voice, floating panels you can drag around, a panel
that shows what the agent is *thinking and doing*, and a hand-tracked cursor (pinch to click and
drag) with no jitter.

## The big picture (read this first)
```
 you speak / type ──► HudWindow ──► AgentWorker (own thread) ──► Agent.run()
                          ▲                                          │
                          │                                  AgentEvents (typed)
   Comms  Mind  Tools  Approval  Reactor  ◄───────────────────────────┘
                          ▲
   Jarvis's voice (TTS) ──► AudioSpectrum (FFT bands) ──► sound-wave ring

 webcam ──► HandTracker (own thread) ──► HandState ──► One Euro filter ──► PinchInteraction
                                                                              │
                                                       click a button / drag a panel
```
Two rules held the whole time: **the agent never imports the UI** (the UI only reads events),
and **a background thread writes, the UI timer reads** (same shape as `AudioLevel`, see [[qt-threading]]).

## Revision map (the 14 topics, in the order we did them)
| # | Topic | One line | Deep dive |
|---|---|---|---|
| 1 | Design first | A mockup and 4 decisions before any code | - |
| 2 | The desk | A window with *no layout*, panels placed by hand | [[hud-desk-and-floating-panels]] |
| 3 | FloatingPanel | Dragging = begin, move, end | [[hud-desk-and-floating-panels]] |
| 4 | Arc reactor | Drawn with `QPainter`; five states | - |
| 5 | Sound-wave ring | Real voice -> FFT -> 36 bars, mirrored | [[fft-audio-spectrum]] |
| 6 | New agent events | A tool reports progress mid-run | [[langgraph-custom-stream]] |
| 7 | Mind panel | A step-by-step trace built only from events | [[agent-event-stream]] |
| 8 | Vitals + threads | Slow reads on a background thread; Windows COM | [[qt-threading]] |
| 9 | Local commands | "interactive mode on" never reaches the LLM | - |
| 10 | Camera -> cursor | Timestamps and a sample counter in `HandState` | [[one-euro-filter]] |
| 11 | Steady cursor | One Euro filter + 2x gain | [[one-euro-filter]] |
| 12 | Click vs drag | Decide by *what is under the cursor* | [[pinch-click-vs-drag]] |
| 13 | Record, replay, tune | Numbers from your real hand, not guesses | [[testing-with-recorded-data]] |
| 14 | Testing hard things | Pure logic + offscreen Qt + replay | [[testing-with-recorded-data]] |

---

## Topic 1: Design first
We made a clickable mockup (an artifact) *before* writing Qt code, then talked about it.
Decisions: one dark full-screen window (not panels over the desktop); arc reactor replaces the old
dotted orb; the ring follows Jarvis's real voice (FFT), not random animation; a **Mind** panel
shows the current request step by step; small screenshot thumbnails; only the current request;
panel positions are *not* saved yet; interactive (hand) mode starts from a dock button or a voice
command.
**Remember:** a picture is the cheapest place to change your mind.

## Topic 2: The desk (a window with no layout)
A normal window uses a *layout* (it decides where children go). Floating panels must sit wherever
you drop them, so the desk has **no layout**. It draws its own background in `paintEvent` and places
children by hand in `resizeEvent` (`setGeometry`). Stacking order is creation order; when a panel is
raised, the desk raises the dock and cursor again so they stay on top.
Speed trick: the grid + vignette never change, so they are painted **once per resize into a pixmap**,
not 60 times a second.
Code: `src/jarvis/ui/hud/window.py`.

## Topic 3: FloatingPanel (dragging in three steps)
```python
panel.begin_drag(point)   # remember where on the panel you grabbed it (an "offset")
panel.drag_to(point)      # move so that same spot stays under the pointer
panel.end_drag()          # forget the offset
```
The mouse (title bar) and the hand cursor call the **same three methods**. Panels are clamped so
you can't drag one off-screen and lose it.
Code: `src/jarvis/ui/hud/panel.py`.

## Topic 4: The arc reactor
Everything is `QPainter` shapes: halo, 72 sound bars, thin ring, rotating tick ring, 10 coil
segments, dark housing, dashed ring, glowing core. Colour = state:
`idle` dim blue, `listening` cyan, `thinking` amber (a "comet" runs round the ring), `waiting`
magenta (needs your approval), `speaking` cyan (bars follow the voice). **"Speaking" is detected
from the audio itself**, with a 0.5 s hold so gaps between words don't flicker it.
Bars use **attack/release smoothing**: jump up fast (60% of the gap per frame), fall slowly (12%).
That is what makes a visualizer look alive instead of jittery.
Code: `src/jarvis/ui/hud/reactor.py`.

## Topic 5: Sound-wave ring (audio -> FFT -> bars)
Loudness alone makes every bar do the same thing. An **FFT** splits sound into pitches, so each
bar follows a different part of Jarvis's real voice. Details in [[fft-audio-spectrum]].
Only *Jarvis's* TTS feeds it - never your mic (you asked for this in Phase 7).
Code: `src/jarvis/voice/audio_spectrum.py`, `tts.py`.

## Topic 6: New agent events (custom stream)
The Mind panel needs "screenshots were taken" and "vision model said X" *while* the tool is still
running. A tool normally only returns at the end. So `inspect_screen` sends progress with
LangGraph's `get_stream_writer()`; the runner turns those dicts into typed events
`ScreenCaptured` and `VisionResult`. Details in [[langgraph-custom-stream]].
Two small bugs found on the way: a direct "look at my screen" request skips the model (the
`screen_intent` node), so its tool call event was missing; and `tool.invoke()` outside a graph raises
`KeyError` (not `RuntimeError`) when asking for the writer.

## Topic 7: The Mind panel
One vertical timeline for the **current request only**. Steps: heard/typed, thinking (with a live
timer), tool call (with its risk tier), screen captured (thumbnails), vision result, result,
answering (token count), and a footer: "2 model calls · 1 tool · total 4.7s". It is built *only*
from `AgentEvent`s plus the UI clock; the agent never knows it exists.
Honest note: Jarvis "thinking" here means *that it is working, and for how long*.
`qwen3:4b-instruct` writes no hidden thoughts. A real **Plan step** (the model writing 1-3 lines
before acting) is **not built yet**.
Code: `src/jarvis/ui/hud/mind.py`.

## Topic 8: Vitals and background threads
CPU/RAM come from `psutil`, VRAM from `nvidia-smi`, volume/brightness from our tools. Brightness
(WMI) and `nvidia-smi` can take 100+ ms, which would stutter the reactor, so a **sampler thread**
reads every 2 s and the UI timer only reads the finished numbers.
Real bug: Windows printed *"Win32 exception occurred releasing IUnknown"* on exit. COM objects belong
to the thread that made them; fix = `CoInitialize()` at the start of the thread, then `gc.collect()`
and `CoUninitialize()` in `finally`, and `join()` the thread on stop. Also `CREATE_NO_WINDOW` so
`nvidia-smi` doesn't flash a console window every 2 s.
Code: `src/jarvis/ui/hud/side_panels.py`.

## Topic 9: Local commands
"Interactive mode on/off" is a UI switch, not a PC task, so a small regex (`commands.py`) handles it
inside the window. Instant, always right, and the agent never needs to know the UI exists.
"What is interactive mode?" has no on/off word, so it goes to the agent normally.
Code: `src/jarvis/ui/hud/commands.py`.

## Topic 10: Camera -> cursor pipeline
`HandTracker` (thread) reads frames and writes `HandState`. We added to it:
- `timestamp`: when the camera frame was *captured* (not when the UI looked at it),
- `seq`: a counter that goes up on every `set()`,
- `pinch_value`: the raw thumb-to-index gap in palm sizes (about 1.0 open, under 0.3 pinched).
Why: the UI timer ticks ~60x/s but the camera gives ~30 samples/s. `seq` lets the UI say "that is a
**new** sample" so each one is filtered **once**, using the real time between samples.
Code: `src/jarvis/vision/hand_state.py`, `hand_tracking.py`.

## Topic 11: Steady cursor (One Euro filter + gain)
Steady when still, quick when you flick. Two separate knobs:
- **Steadiness:** the One Euro filter (heavy smoothing when slow, light when fast).
- **Sensitivity:** `ACTIVE_LOW/HIGH = 0.25/0.75` means only the middle half of the camera image covers
  the screen: a fixed **2x gain**, so small finger moves travel far.
We rejected *mouse-style acceleration*: with absolute pointing it makes the cursor drift away
from where your hand points. See [[one-euro-filter]].
Code: `src/jarvis/vision/pointer.py`, `src/jarvis/ui/hud/gestures.py`.

## Topic 12: Click vs drag
Real problem: *"pinch and drag are getting mixed."* Cause: the cursor moves **30-50 px by itself**
while your fingers close, and the old code decided "drag" from movement (> 12 px). Fix: decide by
**what is under the cursor when the fingers start to close** - button/field = click only, panel =
drag only - and use a short **position history** so the aim point is from just before closing.
See [[pinch-click-vs-drag]].
Code: `src/jarvis/vision/pinch.py`, `src/jarvis/ui/hud/gestures.py`.

## Topic 13: Record, replay, tune
Instead of guessing numbers, we recorded your hand (landmark **numbers only**, no video) with
`examples/phase7b_record_hand.py` and replayed it with `examples/phase7b_tune_cursor.py`.
What the data told us (this is the most important lesson of the phase):
- Camera jitter once your hand is in view and still: only **~3 px** (the scary 10 px came from
  the first 1.5 s of one take, before your hand was in view).
- `FILTER_BETA = 0.02` removed only 6-16% of shake: noise itself looked like fast motion and opened
  the filter. At `0.004`: 31-62% removed, 31-62 ms lag.
- Cursor drift while closing: 35-50 px. That explained the missed clicks.
- 3D "world" pinch distance read 26 mm on a firm pinch, so we kept the 2D ratio for now.
See [[testing-with-recorded-data]].

## Topic 14: Testing the hard-to-test
Qt + camera are awkward to test, so we split the work:
1. **Pure logic** (filter, pinch rules) in plain Python - tested with made-up hands.
2. **Widget tests** off-screen (`tests/ui/conftest.py` sets `QT_QPA_PLATFORM=offscreen`) - a real
   panel and button, a fake hand feeding 30 samples/s.
3. **Replay** on your real recordings as the final check: 4 of 4 quick taps clicked, 3 of 3 drags,
   no stray clicks.
At the end: 117 tests pass. Committed as `6706636`.

---

## Real findings (bugs and surprises, not theory)
- **Test threshold was wrong, not the code.** My "steady" test demanded < 2 px, but the fake shake
  was +-8 px; the filter had already removed ~83%. Fix the *measurement*, not the filter.
- **A metric that lies.** Comparing the filtered path to the *noisy* raw path always picked "0 ms
  lag". Fix: compare against a lightly smoothed copy of the raw path.
- **Contaminated data.** The `still` take started with the hand out of view; the recorder now waits
  until it has seen your hand for 1 s before the countdown.
- **Ruff-style reminders:** unused loop variable `k` (use `_`), lines over 100 chars.
- **Old tests were still right:** the tracking-loss test survived a big rewrite because we kept the
  attribute names it relied on.

## Self-check (answer out loud, then look below)
1. Why does the desk have no layout?
2. What are the three drag methods, and who calls them?
3. Why is the grid drawn into a pixmap once?
4. Why FFT instead of just loudness for the ring? Why are the bands log-spaced?
5. Why does `inspect_screen` use the *stream writer* instead of returning once?
6. Why a sampler thread for Vitals? What does `CoInitialize` fix?
7. Why filter each camera sample once, and what is `seq` for?
8. In the One Euro filter, what do `min_cutoff` and `beta` do?
9. Why was `beta = 0.02` too high on your data?
10. Why can't "moved more than N px" tell a click from a drag?
11. What is "position history", and what does it fix?
12. Why did we not use world landmarks for the pinch (yet)?

### Answers
1. A layout decides child positions; floating panels must stay where the user drops them, so the desk
   places children by hand.
2. `begin_drag`, `drag_to`, `end_drag`; both the mouse (title bar) and the hand cursor.
3. It never changes; redrawing hundreds of lines 60x/s behind the reactor is wasted work.
4. Loudness moves all bars together; FFT gives each bar its own pitch band. Pitch is heard in
   octaves (doubling), so equal-width bands in Hz would give the top bars almost all the range.
5. A tool returns only at the end; the Mind panel wants the screenshots as soon as they exist.
6. Brightness and `nvidia-smi` are slow and would stutter the reactor. COM objects belong to their
   thread; initialising/cleaning up in that thread avoids the exit errors.
7. The camera (~30/s) is slower than the UI timer (~60/s); filtering twice per sample would make the
   smoothing depend on timer luck. `seq` says "this sample is new".
8. `min_cutoff`: lower = steadier when still. `beta`: higher = less lag when moving fast.
9. Camera noise by itself looks like fast motion, so a high `beta` opened the filter and left the
   shake.
10. The cursor already drifts 30-50 px while the fingers close, more than any small threshold.
11. A short list of recent cursor positions; the click/grab uses the position from just before the
    fingers began to close (and the drop from just before they opened), so the drift doesn't count.
12. On the first recording they were noisy in depth (26 mm on a firm pinch). Revisit with more data.

## Not done yet
- Hover highlight and a shrinking pinch ring (so you can *see* what a pinch will hit).
- A visible **Plan** step in the agent (the model writing 1-3 lines before acting).
- Saving panel positions (deliberately later).
- Live tuning after your hand test (`CLICK_MAX_SECONDS`, `ACTIVE_*`, `FILTER_*`).

## How it works (my own words)
_Write this yourself. Pick one: "why a tap used to become a drag", or "why the filter barely helped
until beta changed". Explain it as if telling a friend._

## What confused me / questions I still have
-

## Code to look at
| File | What to read |
|---|---|
| `src/jarvis/ui/hud/window.py` | the desk: paint, layout by hand, events -> panels |
| `src/jarvis/ui/hud/panel.py` | `FloatingPanel` and the three drag steps |
| `src/jarvis/ui/hud/reactor.py` | the arc reactor and the bar smoothing |
| `src/jarvis/voice/audio_spectrum.py` | FFT bands |
| `src/jarvis/agent/runner.py`, `tools/screen.py` | custom stream events |
| `src/jarvis/ui/hud/mind.py` | the step timeline |
| `src/jarvis/vision/pointer.py` | One Euro filter + screen mapping |
| `src/jarvis/vision/pinch.py` | pinch detector and click/drag rules |
| `src/jarvis/ui/hud/gestures.py` | controller: camera sample -> widget action |
| `tests/vision/test_pinch.py`, `tests/ui/test_gestures.py` | the made-up taps and drags |
