# Status

> Resume point. Update at the end of every session.
> To resume after a lost chat: tell Claude "read CLAUDE.md and docs/STATUS.md and continue".

**Last updated:** 2026-11-05
**Current phase:** Phase 7 (voice) code is done. User is also separately editing the Phase 2-6
notes.

## Done
- [x] Phase 0: Foundations. See [[phase-00-foundations]].
- [x] Project structure, tooling (ruff, pytest), docs vault, resume system.
- [x] Phase 1, step 1: tools with `@tool` (`src/jarvis/tools/basic.py`), `bind_tools`, reading raw
      `tool_calls` (`examples/phase1_step1_tool_calls.py`). User ran it; works.
- [x] Phase 1, step 2: the manual tool round trip, `ToolMessage` + `tool_call_id`
      (`examples/phase1_step2_tool_roundtrip.py`).
- [x] Phase 1, steps 3-5: system prompts and templates, structured output, `get_system_info`,
      `run_tool` (errors as text), `make_llm`, switch to `qwen3:4b-instruct`.
- [x] Phase 1 notes: `docs/phases/phase-01-tools.md` plus concepts `tool-calling`,
      `prompt-templates`, `structured-output`, `reasoning-models`.
- [x] Phase 2, steps 1-2: `AgentState` + `add_messages` reducer, the hand-built loop
      (`src/jarvis/agent/graph.py`, `has_tool_calls` conditional edge).
- [x] Phase 2, step 3: swapped in the prebuilt `ToolNode` / `tools_condition`.
- [x] Phase 2, step 4: streaming (`"updates"` vs `"messages"`), proved real token chunks arrive.
- [x] Phase 2, step 5: compared our `build_graph` against `langchain.agents.create_agent`.
- [x] Phase 2 extras: a custom `save_to_db` node with a 3-way router; a real streaming CLI chat
      (`src/jarvis/cli.py`, `uv run python -m jarvis`).
- [x] Phase 2 notes drafted: `docs/phases/phase-02-agent-loop.md` plus concept
      `multi-agent-systems` (deterministic routing vs. agents-as-tools with `create_agent`).
- [x] Phase 3, step 1: `AgentEvent` union - `Thinking`/`Token`/`ToolCall`/`ToolResult`/`Error`
      (`src/jarvis/agent/events.py`).
- [x] Phase 3, step 2: `Agent.run(text) -> Iterator[AgentEvent]`, translating the real stream
      (`src/jarvis/agent/runner.py`). Fixed `ToolMessage` missing `name=` in `run_tool` along the way.
- [x] Phase 3, step 3: rewired `cli.py` onto `Agent.run()` - no LangGraph imports left in the CLI.
- [x] Phase 3 notes drafted: `docs/phases/phase-03-events.md` plus concept `agent-event-stream`.
- [x] Phase 4, step 1: risk tiers - `RiskTier` enum, `@risk_tier` decorator, fail-safe default
      (`src/jarvis/safety/tiers.py`).
- [x] Phase 4, step 2: `interrupt()`/`Command(resume=...)` in isolation; proved nodes rerun from
      the top on resume (`examples/phase4_step2_interrupt_mechanics.py`).
- [x] Phase 4, step 3: the real approval gate (`src/jarvis/safety/approval.py`). Found and fixed a
      real duplicate-tool-execution bug caused by the replay behavior (two-pass decide/run split).
- [x] Phase 4, step 4: wired into `Agent.run()`/`Agent.resume()` and the CLI with a live model;
      `ApprovalRequest` joins the `AgentEvent` union.
- [x] Phase 4, step 5: append-only audit log, one JSONL line per decision
      (`src/jarvis/safety/audit.py`, `.data/audit.log`).
- [x] Phase 4 notes drafted: `docs/phases/phase-04-safety.md` plus concepts `risk-tiers`,
      `interrupt-and-resume`, `audit-log`. Folder allowlists and prompt injection/untrusted
      content deferred to Phase 5, where real file/web tools exist to apply them to.
- [x] Phase 5, step 1: folder allowlist (`.data/workspace/`) + real `open_app` tool
      (`src/jarvis/safety/paths.py`, `src/jarvis/tools/apps.py`).
- [x] Phase 5, step 2: volume/brightness control (AUTO). Found and fixed a COM threading bug -
      LangGraph runs tool code on a worker thread; pycaw needed `CoInitialize()` there too.
- [x] Phase 5, step 3: clipboard read (ASK_ONCE) / write (AUTO), using pywin32.
- [x] Phase 5, step 4: list/read/search files in the workspace sandbox (AUTO).
- [x] Phase 5, step 5: `write_file` - create/overwrite notes (ASK_ONCE).
- [x] Phase 5, step 6: Google Sheets timesheet tools (`src/jarvis/tools/timesheet.py`) - the
      agent's first external API integration. Moved a service-account key out of the workspace
      sandbox after realizing the file tools could have read it. Found and fixed a duplicate-row
      bug caused by small-model sentence-parsing ambiguity (docstring fix, not a code workaround).
- [x] Phase 5, step 7: `delete_file` / `move_file` (ALWAYS_ASK) - the only destructive local ops.
- [x] Phase 5 notes drafted: `docs/phases/phase-05-real-tools.md` plus concept
      `folder-allowlist`. Web search and shell deferred as small follow-ups later.
- [x] Phase 6, step 1: `jarvis/setup.py` - pulled the tool list/`SYSTEM_PROMPT` out of `cli.py`
      so the CLI and the Qt UI share one place that builds the `Agent`.
- [x] Phase 6, step 2: `PySide6-Essentials` added (not the full `pyside6` meta-package - that
      pulls in QtWebEngine, ~125MB we don't need). Main window with a worker `QThread` running
      `Agent.run()`/`resume()`, talking to the GUI thread only through signals/slots
      (`src/jarvis/ui/worker.py`, `src/jarvis/ui/main_window.py`). Run with
      `uv run python -m jarvis.ui`.
- [x] Phase 6, step 3: dark "HUD" theme (`src/jarvis/ui/theme.py`) and a card-based live
      activity timeline (`src/jarvis/ui/timeline.py`, `src/jarvis/ui/cards.py`) replacing a
      single text log - a user message, Jarvis's reply, each tool call/result, and an error are
      each their own widget. An `ApprovalRequest` renders as an inline card with real Yes/No
      buttons (no OS popup), and a bouncing-dots card shows while waiting on the model or a
      tool. Window opens maximized.
- [x] Phase 6, step 4: status bar (`QMainWindow.statusBar()`) showing the live turn state on the
      left and the model name on the right; a generated system tray icon (`src/jarvis/ui/tray.py`)
      - closing the window now hides to the tray instead of quitting, with a Show/Hide/Quit menu.
- [x] Phase 6, step 5: narrowed the chat column and added a right-hand `ToolsPanel`
      (`src/jarvis/ui/tools_panel.py`) listing every tool the agent can call, highlighting
      whichever one is currently running. `jarvis/setup.py` now exposes `build_tools()`
      separately from `build_agent()` so the UI can get the tool names without duplicating the
      list.
- [x] Phase 6 notes drafted: `docs/phases/phase-06-ui.md` plus concept `qt-threading`. The
      deferred UI piece is now specified: a mic button, a listening/speaking visual indicator,
      and a live transcript preview - to be built once voice itself works.
- [x] Phase 7, step 1: speech-to-text, the raw mechanism, no hotkey/agent/UI yet
      (`examples/phase7_step1_stt.py`) - record a fixed clip, transcribe with `faster-whisper`
      (CPU, `base.en`). Found Whisper hallucinating extra sentences during trailing silence;
      fixed with `vad_filter=True` (faster-whisper's built-in Silero VAD, via `onnxruntime` -
      already a transitive dependency, no new install needed). `jarvis/config.py` gained
      `STT_MODEL`/`STT_DEVICE`/`STT_COMPUTE_TYPE`/`SAMPLE_RATE`.
- [x] Phase 7, step 2: text-to-speech, the raw mechanism (`examples/phase7_step2_tts.py`) -
      Piper synthesizes text to audio, played back with `sounddevice`. Voice is
      `en_US-ryan-high` (`jarvis/config.py` `TTS_VOICE`/`TTS_VOICES_DIR`), picked by the user
      for a deeper, more "movie Jarvis" sound over the default `lessac` voice.
- [x] Phase 7, step 3: the full voice loop, still no UI (`examples/phase7_step3_voice_loop.py`)
      - push-to-talk (hold F9, `jarvis/config.py` `PUSH_TO_TALK_KEY`, via `pynput`) records with
      `jarvis/voice/hotkey.py`'s `Recorder`, transcribes with `jarvis/voice/stt.py`, runs it
      through the same `Agent` the CLI uses (so approvals still work), and speaks the reply.
- [x] Phase 7, streaming TTS: fixed the lag from step 3 (Jarvis used to wait for the *entire*
      reply before speaking any of it) - `jarvis/voice/tts.py`'s `SentenceSpeaker` buffers
      streamed tokens and speaks each sentence as soon as it's complete. The voice loop now uses
      a local `speak_and_print()` instead of `cli.render()` so it can feed tokens to the speaker.
- [x] Voice orb, step 1 (replaces a plain listening/speaking indicator - user's idea): a rotating
      sphere made of dots (`src/jarvis/ui/orb.py`), drawn with plain `QPainter` - points placed
      with a Fibonacci sphere distribution, rotated + tilted each frame, depth-shaded (near dots
      bigger/brighter). No 3D engine, no new dependency. Standalone demo:
      `examples/phase7_step4_orb.py`.
- [x] Voice orb, step 2: audio-reactive shape. `jarvis/voice/audio_level.py`'s `AudioLevel` is a
      tiny shared value an audio thread writes and the orb's own frame timer polls (no lock, no
      per-block Qt signal needed). `tts.speak()` now plays through a streaming `sd.OutputStream`
      callback instead of blocking `sd.play()`/`sd.wait()`, updating the level live;
      `voice/hotkey.py`'s `Recorder` does the same for mic input while listening. First attempt
      (independent random wobble per point) looked like chaotic noise and destroyed the sphere's
      shape - fixed with a shared "breathing" pulse plus a small spatially-coherent ripple (based
      on each point's longitude, not randomness) layered on top. Standalone demo:
      `examples/phase7_step5_orb_reactive.py`.
- [x] Mic button wired into the main window (`src/jarvis/ui/main_window.py`): press-and-hold the
      mic button next to the input box to record (same `Recorder` the hotkey uses), release to
      transcribe. `AgentWorker` gained a `transcribe` slot (runs faster-whisper off the GUI
      thread) and a `transcribed` signal. The result fills the input box - it is deliberately
      *not* auto-sent, so you can review/fix a misheard word before clicking Send yourself.
- [x] "Audio mode" (hands-free, continuous listening via live `webrtcvad` silence detection,
      `src/jarvis/voice/audio_mode.py`) was built and the state machine verified correct with a
      scripted speech/silence sequence - but real transcriptions came back coherent-sounding yet
      *wrong* ("completely off", per the user). Parked rather than debugged further: the code and
      its standalone demo (`examples/phase7_step6_audio_mode.py`, which also dumps each captured
      clip to `.data/audio_mode_debug/*.wav` for inspection) are kept for a possible later look,
      but nothing from it is wired into the app.
- [x] Global push-to-talk hotkey wired into the main window instead: hold `PUSH_TO_TALK_KEY`
      (F9) anywhere - even window unfocused - release to auto-transcribe *and* auto-send, with
      the reply spoken aloud. `AgentWorker.send` now takes a `speak: bool` and builds a
      `SentenceSpeaker` for the turn when true. The existing mic *button* deliberately keeps its
      old review-then-Send, silent-reply behavior - two different tools for two different
      moments, not one unified mechanism.
- [x] Found and fixed a real bug: pressing F9 spoke the reply *twice simultaneously*. Root cause
      was environmental, not code - closing a test window now hides it to the tray instead of
      quitting (see Phase 6), so several `uv run python -m jarvis.ui` launches during testing had
      stacked up as separate live processes, each with its own hotkey listener and TTS pipeline.
      Fixed by closing the stale processes; going forward, use "Quit Jarvis" from the tray (or
      close all instances) before relaunching for a test, not just the window's X button.
- [x] Voice orb, step 3: wired into the main window's right panel, below the tools list
      (`src/jarvis/ui/main_window.py`). Only fed by `AgentWorker`'s `SentenceSpeaker` (Jarvis's
      own voice) - the `Recorder` no longer shares the `AudioLevel`, after the user pointed out
      the orb reacting to *their* voice too was wrong; it should only visualize Jarvis speaking.
      Click-to-expand fullscreen: `Orb` gained a `clicked` signal (plain `QWidget`s have none
      built in), hides the chat/tools panels and gives the orb's column layout stretch so it
      fills the window; Esc or clicking again restores the normal layout.

- [x] Webcam hand gestures (`src/jarvis/vision/`), replacing an initial pinch-to-zoom attempt the
      user found unsatisfying. `HandTracker` (background thread, `MediaPipe` `HandLandmarker`)
      classifies the whole hand as open/fist/other and tracks the index fingertip, writing both
      into a `HandState` the orb's frame timer polls - the same "thread writes, UI timer reads"
      pattern as `AudioLevel` (see [[qt-threading]]). Two gestures: moving your index finger
      moves the orb across the screen and squashes it along its direction of travel; closing
      your fist squeezes it, and opening your hand bursts every point outward with its own
      damped spring before it settles back - real per-point transient state, a first for the
      orb (everything before this was a pure function of time + audio level, no memory). Camera
      only runs while the orb is expanded fullscreen, with a visible "CAMERA ACTIVE" label.
      Caught and fixed a real bug via `ruff` (`F841`) while writing this: `pz` was reading
      `spun_z` instead of `tilted_z`, silently dropping the tilt transform from the depth sort.

## Next step
1. User reads and rewrites the "my own words" sections of `phase-02-agent-loop.md` through
   `phase-07-voice.md`, and lists questions; Claude answers them. Then commit the notes.
2. Start Phase 8: memory and context (short-term via checkpointer threads, long-term via the
   LangGraph store, trimming/summarizing for the small model, a remembered user profile). Barge-in
   (interrupting Jarvis mid-sentence) and a wake word are explicitly deferred Phase 7 follow-ups,
   pickable up whenever wanted.

## Open questions
- None yet.

## Environment notes
- Python 3.12 via uv (system Python is 3.14, avoided on purpose).
- GPU is an RTX 3050 with 4 GB VRAM, so stay with 3-4B models; run STT on CPU.
- Ollama has `qwen3:4b-instruct` (default, non-thinking) and `qwen3:4b` (thinking-only; its
  thoughts leak into replies and `reasoning=False` is ignored). See decision 0002.
- `uv run jarvis` can be blocked by Windows Application Control (unsigned generated exe shim).
  Use `uv run python -m jarvis` instead - same code, trusted launcher.
