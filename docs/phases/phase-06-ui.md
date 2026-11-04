# Phase 6: Desktop UI (PySide6)

**Status:** done (one more UI piece deferred to Phase 7 - see Next)
**Date:** 2026-11-04

## Goal
A real desktop window for Jarvis, consuming the exact same `AgentEvent` stream `cli.py` already
uses - no changes to `jarvis.agent` needed, proving Phase 3's design worked.

## What we built
| Step | What | Code |
|---|---|---|
| 1 | `jarvis/setup.py` - pulled the tool list and `SYSTEM_PROMPT` out of `cli.py` so the CLI and the UI share one place that builds the `Agent` | `src/jarvis/setup.py` |
| 2 | Main window + a worker `QThread` running `Agent.run()`/`resume()`, talking to the GUI thread only through signals/slots | `src/jarvis/ui/worker.py`, `src/jarvis/ui/main_window.py` |
| 3 | A dark "HUD" theme, and a card-based live activity timeline (a scrollable list of widgets, one per event) replacing a single text log - with an inline approval card (real Yes/No buttons, no OS popup) and an animated "thinking" card | `src/jarvis/ui/theme.py`, `src/jarvis/ui/timeline.py`, `src/jarvis/ui/cards.py` |
| 4 | Status bar (live turn state + model name) and a generated system tray icon - closing the window now hides to the tray instead of quitting | `src/jarvis/ui/tray.py` |
| 5 | A right-hand sidebar listing every tool the agent can call, highlighting whichever one is currently running | `src/jarvis/ui/tools_panel.py` |

## Concepts learned
- [[qt-threading]]
- Earlier: [[agent-event-stream]], [[interrupt-and-resume]]

## How it works (my own words)
_Write this yourself. Pick one event type (say, `ApprovalRequest`) and trace it end to end: which
thread emits it, which thread receives it, and what turns it into the card you see on screen._

## Things we noticed (real findings, not theory)
- **The full `pyside6` package is heavier than it looks.** It pulls in QtWebEngine
  (~125MB) and PDF tools we never use, and that size kept failing on flaky downloads. Switched to
  `pyside6-essentials`, which has QtCore/QtGui/QtWidgets - everything this UI actually needs.
- **A single shared text log doesn't scale once events interleave.** The first version streamed
  everything (your message, Jarvis's reply, tool calls, tool results) into one `QTextEdit`,
  tracking "the cursor is at the end." That broke the moment a tool call landed *between* a
  reply's streamed tokens: the final answer text ran onto the end of the previous tool-result
  line with no separation. The fix was a real architecture change, not a patch - a scrollable list
  of separate widgets (`cards.py`/`timeline.py`), one per event, so nothing can bleed into
  anything else.
- **A popup breaks the "live" feel.** `QMessageBox.question()` worked, but it's a modal dialog
  disconnected from everything else happening in the window. Replaced it with an `ApprovalCard`
  sitting inline in the timeline with real buttons - closer to how approval prompts look in tools
  like Claude Code.
- **Qt's stylesheet language is CSS-like but limited.** No `box-shadow`, no `letter-spacing`. The
  cyan glow around panels comes from `QGraphicsDropShadowEffect` (a real shadow effect that only
  shows at a fully-opaque widget's edges), and the letter-spaced "J A R V I S" title uses
  `QFont.setLetterSpacing()` - both are Qt/C++ features reached from Python, not CSS.

## What confused me / questions I still have
-

## Code to look at
- `src/jarvis/ui/worker.py`: the whole thread-boundary mechanism, in about 30 lines.
- `src/jarvis/ui/main_window.py`: compare `_on_event` to `cli.py`'s `render()` - the same
  event-handling shape, just pushed to us via a signal instead of pulled in a `for` loop.
- `src/jarvis/ui/cards.py`: the widget-per-event design that fixed the text-log bug.

## Next
[[PLAN]] One more UI piece is still wanted, intentionally deferred until Phase 7 (voice) starts -
not yet specified. Otherwise, next up is Phase 7: voice (VAD, `faster-whisper` STT, Piper TTS,
push-to-talk hotkey, barge-in), wired into this same window.
