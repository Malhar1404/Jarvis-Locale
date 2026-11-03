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

## Phase 2: The agent loop in LangGraph
Concepts: `StateGraph`, state and reducers (`add_messages`), nodes, edges, conditional edges, `ToolNode`,
the ReAct loop, streaming modes (`updates`, `messages`). Then compare with the prebuilt `create_agent`.
Build: the loop by hand (`llm_node -> tools -> llm_node -> END`), a CLI chat with streaming.
Done when: you can draw the graph, and you know what `create_agent` does for you and what it hides.

## Phase 3: Seeing what the agent does (events and observability)
Concepts: turning the raw stream into our own typed events (`Thinking`, `ToolCall`, `ToolResult`,
`Token`, `ApprovalRequest`, `Error`), logging, optional tracing (LangSmith or self-hosted Langfuse).
Build: an `AgentEvent` model plus an `agent.run(text) -> Iterator[AgentEvent]` API; the CLI renders it as a timeline.
Done when: the same event stream could drive any UI. This is what the Qt activity panel will consume.

## Phase 4: Safety and human-in-the-loop
Concepts: checkpointers (SQLite), threads, `interrupt()`, `Command(resume=...)`, risk tiers
(auto / ask once / always ask / never), folder allowlists, prompt injection and untrusted content, audit log.
Build: a policy layer wrapping every tool, an approve/deny flow in the CLI, an append-only audit log.
Done when: a "delete this file" request pauses, shows the exact action, and does nothing until you approve.

## Phase 5: Real PC tools
Concepts: tool design (small, specific, good descriptions, errors returned to the model as text), Windows APIs.
Build, in order of risk: open apps, volume/brightness, clipboard, list/read/search files in allowed folders,
create notes and reminders, create/move/delete files (gated), web search (untrusted output), shell (always gated).
Done when: 6-8 everyday tasks work reliably with the 4B model, each with a correct risk tier.

## Phase 6: Desktop UI (PySide6)
Concepts: Qt event loop, signals/slots, worker threads (`QThread`) so the UI never freezes, model/view.
Build: main window with chat, a live activity timeline (thinking / tool call / result / waiting for approval),
a native approval dialog, status bar (model, listening state), system tray icon. Consumes phase 3 events.
Done when: you can run a task and watch every step happen in the UI.

## Phase 7: Voice
Concepts: VAD, STT (`faster-whisper` on CPU), TTS (Piper), push-to-talk with a global hotkey, streaming TTS
sentence by sentence, barge-in (interrupt while speaking), optional wake word (openWakeWord).
Build: hotkey -> record -> transcribe -> agent -> speak. UI shows idle / listening / thinking / speaking.
Done when: you can run an everyday task entirely by voice, including a spoken approval.

## Phase 8: Memory and context
Concepts: short-term memory (checkpointer threads), long-term memory (LangGraph store), trimming and
summarizing context (important for a small model), user profile and preferences.
Build: remembers your name, folders, and preferences across restarts; conversations resume.
Done when: "open my usual project folder" works after a restart.

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
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5
- [ ] Phase 6
- [ ] Phase 7
- [ ] Phase 8
- [ ] Phase 9
- [ ] Phase 10
