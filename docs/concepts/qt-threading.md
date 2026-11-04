# Qt's threading model: QThread + signals/slots

**One line:** the GUI thread must never block, so slow work (like `Agent.run()`) runs on a
separate `QThread`, and the two threads only ever talk through signals and slots - never by
calling each other's methods directly.

## Why it exists
A desktop app has one event loop that redraws the window and reacts to clicks. If that same
thread calls something slow - like waiting on the LLM, or on a tool - the whole window freezes:
no redraw, no click response, nothing, until the slow call returns. `Agent.run()`/`resume()` are
blocking generators (see [[agent-event-stream]]), so they cannot run on the main thread.

## How it works
`AgentWorker` (`src/jarvis/ui/worker.py`) is a `QObject` moved onto its own `QThread`:
```python
self._thread = QThread()
self._worker = AgentWorker(agent)
self._worker.moveToThread(self._thread)
self._worker.event.connect(self._on_event)          # worker thread -> main thread
self.send_requested.connect(self._worker.send)       # main thread -> worker thread
self._thread.start()
```
`send_requested` is a `Signal(str)` defined on the *main-thread* `MainWindow`. `AgentWorker.send`
is a `@Slot(str)`. Because the worker object lives on a different thread than the window, Qt
detects this when the connection is made and automatically turns it into a **queued connection**:
calling `self.send_requested.emit(text)` does not run `worker.send(text)` immediately - it posts
an event onto the worker thread's queue, and the worker thread picks it up and runs it on its own
time. The reverse direction (`worker.event.connect(self._on_event)`) works the same way: the
worker thread emits, and `_on_event` actually runs on the main thread.

This is why the main thread must **never call `self._worker.send(text)` directly** - that would
just run the slow code on the main thread by accident, defeating the whole point. Everything
crosses the thread boundary through `.emit(...)`, never a plain method call.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| `QThread` + signals/slots (this) | The standard Qt way; Qt handles the queueing for you | - |
| `asyncio` + `qasync` | An app that is async throughout | `Agent.run()` is a plain blocking generator, and we'd add a dependency just to bridge two different concurrency models |
| Call `agent.run()` directly on the main thread | Simplest code, no threading at all | The window freezes for the whole LLM reply - not acceptable for a voice assistant |
| `QRunnable` + `QThreadPool` | Many short, independent background jobs | We have exactly one long-lived worker per window, not a pool of one-off tasks - a dedicated `QThread` is a better fit |

## Related
- [[agent-event-stream]]
- [[interrupt-and-resume]]
