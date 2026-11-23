# Jarvis: Learning Plan

Goal: a local voice assistant (Ollama + LangChain/LangGraph + PySide6) that does everyday PC tasks,
asks permission before anything risky, and shows live what the agent is thinking and doing.

Rules for the project
- One phase at a time. Each phase ends with something that runs, and a short "what did I learn" recap.
- The agent core (`jarvis/agent`) never imports UI code. The CLI and the Qt app are thin front-ends.
- Permissions are enforced in Python code, never only in the prompt.
- The hardware is a 4 GB VRAM GPU, so the model is small (`qwen3:4b`). Few, clearly described tools; STT runs on CPU.

Target layout (grows phase by phase)
```
src/jarvis/
  agent/      graph, state, prompts, event stream      (phases 2-3)
  tools/      one file per tool group, each with a risk tier (phases 1, 5)
  safety/     permission policy, approvals, audit log  (phase 4)
  memory/     checkpointer + long-term store           (phase 8)
  voice/      stt, tts, vad, hotkey                    (phase 7)
  ui/         PySide6 app                              (phase 6)
  config.py  cli.py  __main__.py                       (cli grows from phase 2)
tests/        mirrors src/
examples/     small learning scripts, one or more per phase
docs/         Obsidian vault: STATUS.md, PLAN.md, phases/, concepts/, decisions/, templates/
.data/        gitignored runtime data (SQLite checkpoints, audit log)
```

---

## Phase 0: Foundations  (done)
- Built: uv project on Python 3.12, Ollama + `qwen3:4b`, `hello_llm.py`.
- Learned: chat models, message types (System/Human/AI), `invoke` vs `stream`.

## Phase 1: Prompts, structured output, and tools  (done)
Concepts: prompt templates, `with_structured_output` (Pydantic), the `@tool` decorator, tool schemas,
`bind_tools`, what a `tool_call` actually is (the model asks, it does not run anything).
Build: 2-3 harmless tools (`get_time`, `get_system_info`, `calculator`). Call the model with tools bound,
print the raw `tool_calls`, execute the tool by hand, send back a `ToolMessage`, get the final answer.
Done when: you can explain the full tool-calling round trip without a framework hiding it.

## Phase 2: The agent loop in LangGraph  (done)
Concepts: `StateGraph`, state and reducers (`add_messages`), nodes, edges, conditional edges, `ToolNode`,
the ReAct loop, streaming modes (`updates`, `messages`). Then compare with the prebuilt `create_agent`.
Build: the loop by hand (`llm_node -> tools -> llm_node -> END`), a CLI chat with streaming.
Done when: you can draw the graph, and you know what `create_agent` does for you and what it hides.

## Phase 3: Seeing what the agent does (events and observability)  (done)
Concepts: turning the raw stream into our own typed events (`Thinking`, `ToolCall`, `ToolResult`,
`Token`, `ApprovalRequest`, `Error`), logging, optional tracing (LangSmith or self-hosted Langfuse).
Build: an `AgentEvent` model plus an `agent.run(text) -> Iterator[AgentEvent]` API; the CLI renders it as a timeline.
Done when: the same event stream could drive any UI. This is what the Qt activity panel will consume.

## Phase 4: Safety and human-in-the-loop  (done)
Concepts: checkpointers (SQLite), threads, `interrupt()`, `Command(resume=...)`, risk tiers
(auto / ask once / always ask / never), folder allowlists, prompt injection and untrusted content, audit log.
Build: a policy layer wrapping every tool, an approve/deny flow in the CLI, an append-only audit log.
Done when: a "delete this file" request pauses, shows the exact action, and does nothing until you approve.

## Phase 5: Real PC tools  (done)
Concepts: tool design (small, specific, good descriptions, errors returned to the model as text), Windows APIs,
folder allowlists, and treating file/web content as untrusted input.
Built: open apps, volume/brightness, clipboard read/write, list/read/search/write/delete/move files in the
workspace sandbox (folder allowlist), and a Google Sheets timesheet integration (list tabs, read a tab,
add/merge an entry) - the agent's first external API tool, scoped to one fixed spreadsheet ID.
Done when: 6-8 everyday tasks work reliably with the 4B model, each with a correct risk tier. (Exceeded -
13 tools built.) Deferred as later follow-ups: web search (untrusted content input) and shell (always gated).

## Phase 6: Desktop UI (PySide6)  (done)
Concepts: Qt event loop, signals/slots, worker threads (`QThread`) so the UI never freezes, model/view.
Built: main window with chat, a dark "HUD" theme, a card-based live activity timeline (thinking /
tool call / result / inline approval with real Yes/No buttons), status bar (live state, model
name), system tray icon (hide-to-tray), and a bonus tools sidebar highlighting the tool in use.
Consumes phase 3 events with zero changes to `jarvis.agent`.
Done when: you can run a task and watch every step happen in the UI. (Done - one more UI piece
intentionally deferred to Phase 7, once voice needs it.)

## Phase 7: Voice  (done)
Concepts: VAD (both post-hoc clip cleanup and live silence detection), STT (`faster-whisper` on
CPU), TTS (Piper, streaming sentence by sentence), push-to-talk with a global hotkey, webcam hand
gestures (MediaPipe Hands) controlling a new rotating-dot voice orb.
Built: hotkey -> record -> transcribe -> agent -> speak, wired into the Qt UI alongside a
review-before-send mic button. The orb deforms with Jarvis's own speech volume and responds to
hand gestures (finger-follow, fist squeeze/burst) when expanded fullscreen.
Done when: you can run an everyday task entirely by voice, including a spoken reply. (Done -
barge-in and a wake word were concepts on the list but aren't required by this bar; deferred, along
with a hands-free "Audio mode" that was built but didn't transcribe reliably enough to ship.)

## Phase 7b: HUD redesign (floating panels, arc reactor, Mind panel, gestures)
Mockup (confirmed by user 2026-11-18): https://claude.ai/artifact/R95HeuKL1AcSVCiy9xY866
Decisions: one dark full-screen window (panels live inside it, not over the desktop); arc reactor
fully replaces the dotted-sphere orb; its sound-wave ring is driven by FFT frequency bands of
Jarvis's own TTS audio (not random, not the user's mic); a visible plan step ("Jarvis should be
thinking"); Mind panel shows only the current request, small screenshot thumbnails; panel
positions are NOT saved yet (later); interactive mode is toggled by a dock button or a voice command.
Steps:
1. Shell: full-screen dark window, grid background, top bar, bottom dock.
2. `FloatingPanel`: drag by title bar, raise on click, show/hide from the dock.
3. Move existing parts into panels: Comms (chat + mic), Tools, Approval pop-up; new Vitals (psutil).
4. Arc reactor (`QPainter`) with idle / listening / thinking / speaking states from agent events.
5. Sound-wave ring: FFT bands from TTS playback, shared like `AudioLevel`.
6. Plan step in the graph + new `Plan` / `ScreenCaptured` events + the Mind panel.
7. Interactive mode: camera on, virtual cursor follows the index finger, pinch = grab/drag a panel.
   Robustness pass (decided 2026-11-18; problems seen: cursor shake, missed clicks, drag drops/sticks;
   feel wanted: steady when still, but small finger moves travel far):
   a. `examples/` recorder saves ~10 s of hand landmark numbers (no video) to `.data/`, replayed in tests.
   b. One Euro filter (heavy smoothing when slow/still, light when flicking) applied in screen
      pixels using real camera timestamps, plus a higher fixed gain (smaller camera region covers
      the screen); replaces the deadzone/EMA in `ui/hud/gestures.py`. Mouse-style acceleration was
      rejected: with absolute pointing it makes the cursor drift away from where the hand points.
   c. DONE: pinch = 2D thumb-index gap / palm size, hysteresis + 2 consecutive frames to switch
      (`vision/pinch.py`). Not MediaPipe *world* landmarks for now: on the first recordings their
      thumb-index distance read 26 mm on a firm pinch (3D depth is noisy). Revisit with more data.
   d. DONE: click vs drag is decided by WHAT IS UNDER THE CURSOR when the fingers start closing
      (button/field = click only, panel = drag only, quick tap on a panel = raise), not by
      movement - the cursor drifts 30-50 px by itself while the fingers close. Click/grab target =
      position from just before the fingers closed, drop = just before they opened (position
      history); drag distance measured from where the pinch closed; tracking-loss grace, then
      cancel and restore the panel. Replayed on real takes: 4/4 quick taps clicked, 3/3 drags, no
      stray clicks. Still open: pinch held > 0.8 s is not a click (`CLICK_MAX_SECONDS`).
   e. Feedback: hover highlight, shrinking pinch ring, small hit-target slop, raw-vs-filtered debug view.
8. Phase note and concept notes.
Done when: you can talk to Jarvis, watch the reactor react to its voice, see its plan and screenshots
in the Mind panel, and move panels with a pinch.

## Phase 8: Memory and context
Concepts: short-term memory (checkpointer threads), long-term memory (LangGraph store), trimming and
summarizing context (important for a small model), user profile and preferences.
Built: short-term memory via the checkpointer (done earlier); long-term memory via a sqlite-backed
LangGraph `Store` (`remember_fact`/`recall_fact`/`list_remembered_facts`), with the system prompt
now nudging the model to remember things on its own, not just when asked; an explicit context
window (`num_ctx`) and a trim budget (`trim_messages`) so an old conversation can't silently
overflow the model; `/compact` to summarize old messages into a kept summary instead of just
dropping them, with live context-usage shown in the HUD.
Done when: "open my usual project folder" works after a restart. (Built, not yet tried live.)

## Phase 9: Polish and stretch goals
- Startup: autostart with Windows, tray-only mode, a greeting when the app starts.
- Reliability: a small test set of tasks (an eval) to compare models and prompts.
- Stretch: MCP tools via `langchain-mcp-adapters`, vision (`qwen2.5-vl`) for "what is on my screen",
  planner/executor or multi-agent split, packaging as an `.exe` with PyInstaller.

## Phase 10: How LLMs actually work (architecture and training)
The capstone: Jarvis is built, now open up what was inside the box the whole time.
Concepts: tokenization, embeddings, the transformer block (self-attention + feed-forward),
query/key/value, multi-head attention, positional encoding, causal masking (why a model only
sees tokens *before* the current one - this is also why it can't "go back" and edit earlier
text), context length. Training stages: pretraining (next-token prediction on huge text),
instruction fine-tuning, and preference tuning/RLHF - and specifically how "thinking" models
(e.g. `qwen3-thinking`, seen in [[reasoning-models]]) are trained to produce a long reasoning
trace before answering, versus an instruct model trained to answer directly.
Build: a tiny hands-on demo, no real training, in the same style as
`examples/phase2_extra_custom_node_wiring.py` - a minimal self-attention mechanism in plain
Python/NumPy on a toy sequence, so you see the Q/K/V math and attention weights with your own
eyes instead of only reading about them. Likely also: tokenize a real sentence and look at the
actual tokens, tying back to the Ollama chat template we inspected in [[reasoning-models]].
Done when: you can explain, in your own words, why a model can only ever produce text (closing
the loop on [[tool-calling]] - "why can't the model just run the code itself"), roughly what
attention does, and how pretraining + fine-tuning + RLHF produced a model that can chat, call
tools, and sometimes think before answering.

---

## Progress
(The live status and next step are in [[STATUS]].)

- [x] Phase 0
- [x] Phase 1
- [x] Phase 2
- [x] Phase 3
- [x] Phase 4
- [x] Phase 5
- [x] Phase 6
- [x] Phase 7
- [x] Phase 7b (HUD redesign)
- [ ] Phase 8
- [ ] Phase 9
- [ ] Phase 10
