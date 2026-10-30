# 0001: PySide6 desktop UI, no web server

**Decision:** native Windows app with PySide6 (Qt), agent runs in-process on a worker thread.

**Why:** tray icon, global hotkey and overlay fit a Jarvis-style assistant; one Python project,
no FastAPI/WebSocket layer to learn or debug.

**Trade-off:** Qt threads and signals take time to learn. The agent core stays UI-independent so
the UI can be replaced later.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Flet | Fastest modern-looking UI, little code | Fewer low-level desktop hooks (hotkey, overlay); fallback if Qt is too hard |
| CustomTkinter | Very simple apps | Dated look, weak for a live timeline and voice UI |
| Tauri / Electron + React | Best-looking UI | A web app in disguise; needs a separate Python backend |
| Web app (FastAPI + React) | Remote access, best UI ceiling | Extra server layer; not a native Windows app |
| Streamlit / Gradio | Quick demos | Not a real desktop app; no tray or hotkey |
