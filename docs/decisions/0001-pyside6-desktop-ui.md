# 0001: PySide6 desktop UI, no web server

**Decision:** native Windows app with PySide6 (Qt), agent runs in-process on a worker thread.

**Why:** tray icon, global hotkey and overlay fit a Jarvis-style assistant; one Python project,
no FastAPI/WebSocket layer to learn or debug.

**Trade-off:** Qt threads and signals take time to learn. The agent core stays UI-independent so
the UI can be replaced later.
