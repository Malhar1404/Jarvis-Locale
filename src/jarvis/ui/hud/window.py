"""The HUD window: a frameless full-screen "desk" with floating panels and the arc reactor.

The desk has NO layout on purpose. A layout decides where children go; floating panels must sit
wherever the user drops them. So the desk paints its own background (paintEvent) and places
its children by hand with setGeometry(). resizeEvent re-anchors the fixed pieces (top bar,
reactor, dock) whenever the window size changes.

Stacking order (z-order) is creation order, bottom to top: reactor, panels, dock, hand cursor.
A panel brought to the front with raise_() would cover the dock and cursor, so every time one
is raised the desk raises those two again (_keep_overlays_on_top).

Like the old MainWindow, this only knows the AgentEvent stream - nothing about LangGraph.
"""

from PySide6.QtCore import QDateTime, QPointF, QRectF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSystemTrayIcon,
    QWidget,
)

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    ScreenCaptured,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
    VisionResult,
)
from jarvis.agent.runner import Agent
from jarvis.config import MODEL, PUSH_TO_TALK_KEY, VISION_MODEL
from jarvis.ui import theme
from jarvis.ui.hud.commands import compact_command, interactive_mode_command
from jarvis.ui.hud.comms import CommsView, ReplyBubble
from jarvis.ui.hud.gestures import CursorOverlay, GestureController
from jarvis.ui.hud.mind import MindView
from jarvis.ui.hud.panel import FloatingPanel
from jarvis.ui.hud.reactor import ArcReactor
from jarvis.ui.hud.side_panels import ApprovalView, ToolsView, VitalsSampler, VitalsView
from jarvis.ui.hud.style import (
    EDGE_MARGIN,
    STATE_COLORS,
    STATE_LABELS,
    STYLESHEET,
    TITLE_FONT,
)
from jarvis.ui.tray import Tray, make_icon
from jarvis.ui.worker import AgentWorker
from jarvis.voice.audio_spectrum import AudioSpectrum
from jarvis.voice.hotkey import Recorder, listen_push_to_talk

GRID_STEP = 48  # px between background grid lines
TOP = 84  # y where panels start, below the top bar
DOCK_SPACE = 90  # px kept free at the bottom for the dock


class TopBar(QWidget):
    """Title, status and camera indicator on the left; date, clock, minimise, hide on the right."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        title = QLabel("J.A.R.V.I.S", objectName="hudTitle")
        title_font = QFont(TITLE_FONT)
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        title.setFont(title_font)

        dot = QLabel("●", objectName="hudOnlineDot")
        status = QLabel(f"ONLINE · {MODEL} · {VISION_MODEL} · local", objectName="hudStatus")
        self.context_label = QLabel("", objectName="hudStatus")
        self.camera_label = QLabel("● CAMERA ACTIVE", objectName="hudCamera")
        self.camera_label.hide()
        self.date_label = QLabel(objectName="hudDate")
        self.clock_label = QLabel(objectName="hudClock")
        self.minimize_button = QPushButton("–", objectName="topButton")
        self.minimize_button.setToolTip("Minimise")
        self.close_button = QPushButton("×", objectName="topButton")
        self.close_button.setToolTip("Hide to tray (Jarvis keeps running)")

        row = QHBoxLayout(self)  # a layout INSIDE the bar is fine - the bar itself never moves
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(title)
        row.addSpacing(8)
        row.addWidget(dot)
        row.addWidget(status)
        row.addSpacing(12)
        row.addWidget(self.context_label)
        row.addSpacing(12)
        row.addWidget(self.camera_label)
        row.addStretch()
        row.addWidget(self.date_label)
        row.addSpacing(8)
        row.addWidget(self.clock_label)
        row.addSpacing(12)
        row.addWidget(self.minimize_button)
        row.addWidget(self.close_button)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _tick(self) -> None:
        now = QDateTime.currentDateTime()
        self.date_label.setText(now.toString("ddd dd MMM").upper())
        self.clock_label.setText(now.toString("HH:mm"))

    def set_context_usage(self, used: int, budget: int) -> None:
        pct = min(100, 100 * used // budget) if budget else 0
        self.context_label.setText(f"{used}/{budget} TOK ({pct}%)")


class Dock(QFrame):
    """Bottom-centre bar: one toggle per panel, then the Interactive-mode switch. It only
    *announces* clicks through signals; the window decides what they mean.
    """

    toggled = Signal(str, bool)  # panel name, now visible?
    interactive_toggled = Signal(bool)

    def __init__(self, parent: QWidget, names: list[str]) -> None:
        super().__init__(parent, objectName="hudDock")
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(8)
        self.buttons: dict[str, QPushButton] = {}
        for name in names:
            button = QPushButton(name, objectName="dockButton", checkable=True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            # name=name freezes the current value; a bare lambda would only see the last name
            button.toggled.connect(lambda checked, name=name: self.toggled.emit(name, checked))
            row.addWidget(button)
            self.buttons[name] = button
        divider = QFrame(objectName="dockDivider")
        divider.setFixedSize(1, 24)
        row.addWidget(divider)
        self.interactive_button = QPushButton(
            "Interactive", objectName="dockInteractive", checkable=True
        )
        self.interactive_button.setToolTip("Webcam hand control: pinch to grab panels")
        self.interactive_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.interactive_button.toggled.connect(self.interactive_toggled.emit)
        row.addWidget(self.interactive_button)

    def set_checked_quietly(self, button: QPushButton, checked: bool) -> None:
        """Update a button's look without firing its signal (avoids feedback loops)."""
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)


class HudWindow(QWidget):
    # Crossing from this (main) thread into the worker's thread must go through signals - Qt
    # then queues the call onto the worker's thread instead of running it here by mistake.
    send_requested = Signal(str, bool)  # text, speak_the_reply
    resume_requested = Signal(str)
    transcribe_requested = Signal(object)  # a recorded numpy clip
    compact_requested = Signal()  # /compact typed in the chat box
    hotkey_pressed = Signal()  # pynput calls these from its own thread, not the GUI thread
    hotkey_released = Signal()

    def __init__(self, agent: Agent, tool_tiers: dict[str, str]) -> None:
        super().__init__()
        self.setObjectName("hud")
        self.setWindowTitle("Jarvis")
        self.setWindowIcon(make_icon())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)  # no Windows title bar or border
        self.setStyleSheet(STYLESHEET)
        palette = self.palette()  # default text colour for every child (labels, buttons)
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text):
            palette.setColor(role, QColor(theme.TEXT))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.TEXT))
        self.setPalette(palette)
        self._quitting = False
        self._background: QPixmap | None = None
        self._layout_done = False

        # -- the pieces on the desk, bottom to top ---------------------------------------
        self._spectrum = AudioSpectrum()  # fed only by Jarvis's own TTS, never your mic
        self.top_bar = TopBar(self)
        self.reactor = ArcReactor(self, self._spectrum)
        self.reactor_label = QLabel(STATE_LABELS["idle"], self, objectName="reactorState")
        self.reactor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state_font = QFont(TITLE_FONT)
        state_font.setPixelSize(17)
        state_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 8)
        self.reactor_label.setFont(state_font)
        self.reactor_caption = QLabel("", self, objectName="reactorCaption")
        self.reactor_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reactor.state_changed.connect(self._on_reactor_state)
        self._on_reactor_state("idle")

        self.comms = CommsView()
        self.mind = MindView(MODEL, VISION_MODEL, tool_tiers)
        # The agent object itself is still safe to read here - the worker thread it will live on
        # hasn't started yet (see self._thread.start() below) - so a resumed conversation shows
        # its real stored usage immediately, not just after the next turn.
        self.top_bar.set_context_usage(*agent.context_usage())
        self.mind.set_context_usage(*agent.context_usage())
        self._vitals_sampler = VitalsSampler()
        self.vitals = VitalsView(self._vitals_sampler)
        self.tools_view = ToolsView(tool_tiers)
        self.approval_view = ApprovalView()
        self.panels: dict[str, FloatingPanel] = {
            "Comms": FloatingPanel(
                self, "Comms", "COMMS", theme.ACCENT, self.comms, QSize(400, 520)
            ),
            "Mind": FloatingPanel(
                self,
                "Mind",
                "MIND",
                theme.TOOL,
                self.mind,
                QSize(440, 640),
                subtitle="internal processing",
            ),
            "Vitals": FloatingPanel(
                self, "Vitals", "VITALS", theme.ACCENT, self.vitals, QSize(380, 230)
            ),
            "Tools": FloatingPanel(
                self, "Tools", "TOOLS", theme.ACCENT, self.tools_view, QSize(420, 330)
            ),
        }
        self.approval_panel = FloatingPanel(
            self,
            "Approval",
            "APPROVAL NEEDED",
            theme.APPROVAL,
            self.approval_view,
            QSize(440, 200),
            closable=False,
            background="rgb(22, 9, 30)",  # fully opaque: it covers the reactor's label
        )
        self.panels["Tools"].hide()
        self.approval_panel.hide()
        for panel in [*self.panels.values(), self.approval_panel]:
            panel.moved.connect(self.update)  # repaint the glow behind it
            panel.raised.connect(self._keep_overlays_on_top)
            panel.hidden_by_user.connect(self._on_panel_hidden)

        self.dock = Dock(self, list(self.panels))
        for name, panel in self.panels.items():
            self.dock.set_checked_quietly(self.dock.buttons[name], not panel.isHidden())
        self.dock.toggled.connect(self._on_dock_toggled)
        self.dock.interactive_toggled.connect(self._set_interactive)

        self.cursor_overlay = CursorOverlay(self)
        self.gestures = GestureController(self, self.cursor_overlay)

        self.top_bar.minimize_button.clicked.connect(self.showMinimized)
        self.top_bar.close_button.clicked.connect(self.close)

        # -- voice + agent plumbing (same flow as the old MainWindow) --------------------
        self._recorder = Recorder()
        self._recording = False
        self._busy = False
        self._voice_auto_send = False  # set just before a release, read when transcription lands
        self._voice_turn = False  # True if the text about to be sent came from voice input
        self._reply: ReplyBubble | None = None

        self.comms.send_button.clicked.connect(self._on_send)
        self.comms.input_line.returnPressed.connect(self._on_send)
        self.comms.mic_button.pressed.connect(self._start_recording)
        self.comms.mic_button.released.connect(lambda: self._stop_recording(auto_send=False))
        self.hotkey_pressed.connect(self._start_recording)
        self.hotkey_released.connect(lambda: self._stop_recording(auto_send=True))
        # These callbacks run on pynput's own thread - they may only emit a signal.
        self._hotkey_listener = listen_push_to_talk(
            PUSH_TO_TALK_KEY, self.hotkey_pressed.emit, self.hotkey_released.emit
        )
        self.approval_view.decided.connect(self._on_approval_decided)

        self.tray: Tray | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(self)
            self.tray.show()

        self._thread = QThread()
        self._worker = AgentWorker(agent, level=self._spectrum)
        self._worker.moveToThread(self._thread)
        self._worker.event.connect(self._on_event)
        self._worker.turn_done.connect(self._on_turn_done)
        self._worker.transcribed.connect(self._on_transcribed)
        self._worker.compacted.connect(self._on_compacted)
        self._worker.context_usage.connect(self._on_context_usage)
        self.send_requested.connect(self._worker.send)
        self.resume_requested.connect(self._worker.resume)
        self.transcribe_requested.connect(self._worker.transcribe)
        self.compact_requested.connect(self._worker.compact)
        self._thread.start()
        self._vitals_sampler.start()

    # ================================================================== painting & layout
    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        if self._background is not None:
            painter.drawPixmap(0, 0, self._background)
        # A soft glow around each visible panel: a few rounded outlines, fading outward.
        # (Cheaper and crisper than QGraphicsDropShadowEffect on a widget full of text.)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for panel in [*self.panels.values(), self.approval_panel]:
            if panel.isHidden():
                continue
            rect = QRectF(panel.geometry())
            for step in range(1, 7):
                glow = QColor(panel.color)
                glow.setAlpha(34 - step * 5)
                painter.setPen(QPen(glow, 2))
                outline = rect.adjusted(-step, -step, step, step)
                painter.drawRoundedRect(outline, 10 + step, 10 + step)

    def _paint_background(self) -> None:
        """Grid + vignette never change, so draw them once per resize into a pixmap. The reactor
        repaints 60 times a second, and redrawing hundreds of grid lines behind it every frame
        would be wasted work.
        """
        w, h = self.width(), self.height()
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor(theme.BG))
        p = QPainter(pixmap)
        p.setPen(QPen(QColor(0, 229, 255, 11), 1))
        for x in range(0, w, GRID_STEP):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, GRID_STEP):
            p.drawLine(0, y, w, y)
        glow = QRadialGradient(QPointF(w / 2, h * 0.45), max(w, h) * 0.75)
        glow.setColorAt(0.0, QColor(0, 229, 255, 22))
        glow.setColorAt(0.42, QColor(5, 8, 15, 0))
        glow.setColorAt(1.0, QColor(0, 0, 0, 140))
        p.fillRect(pixmap.rect(), glow)
        p.end()
        self._background = pixmap

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._paint_background()
        self.top_bar.setGeometry(EDGE_MARGIN, 22, w - 2 * EDGE_MARGIN, 40)

        size = min(int(min(w, h) * 0.55), 560)
        cx, cy = w // 2, int(h * 0.44)
        self.reactor.setGeometry(cx - size // 2, cy - size // 2, size, size)
        self.reactor_label.setGeometry(cx - 260, cy + size // 2 + 2, 520, 28)
        self.reactor_caption.setGeometry(cx - 300, cy + size // 2 + 32, 600, 22)

        self.dock.adjustSize()  # shrink-wrap the dock to its buttons
        self.dock.move((w - self.dock.width()) // 2, h - self.dock.height() - 18)
        self.cursor_overlay.setGeometry(self.rect())

        if not self._layout_done:
            self._place_panels_first_time(w, h, cy, size)
            self._layout_done = True
        else:
            for panel in [*self.panels.values(), self.approval_panel]:
                panel.move_clamped(panel.pos())  # keep panels on screen if the window shrank
        self._keep_overlays_on_top()

    def _place_panels_first_time(self, w: int, h: int, cy: int, reactor_size: int) -> None:
        vitals, comms = self.panels["Vitals"], self.panels["Comms"]
        mind, tools = self.panels["Mind"], self.panels["Tools"]
        vitals.move(EDGE_MARGIN, TOP)
        comms_top = TOP + vitals.height() + 20
        comms.setGeometry(
            EDGE_MARGIN, comms_top, comms.width(), max(320, h - comms_top - DOCK_SPACE)
        )
        mind.setGeometry(
            w - EDGE_MARGIN - mind.width(), TOP, mind.width(), min(680, h - TOP - DOCK_SPACE)
        )
        tools.move(w - EDGE_MARGIN - tools.width() - mind.width() - 20, TOP)
        self.approval_panel.move(
            (w - self.approval_panel.width()) // 2,
            min(cy + reactor_size // 4, h - DOCK_SPACE - self.approval_panel.height()),
        )

    def _keep_overlays_on_top(self) -> None:
        self.dock.raise_()
        self.cursor_overlay.raise_()

    # ============================================================== panels, dock, modes
    def _on_dock_toggled(self, name: str, visible: bool) -> None:
        panel = self.panels[name]
        panel.setVisible(visible)
        if visible:
            panel.move_clamped(panel.pos())
            panel.bring_to_front()

    def _on_panel_hidden(self, key: str) -> None:
        if key in self.dock.buttons:
            self.dock.set_checked_quietly(self.dock.buttons[key], False)

    def _set_interactive(self, on: bool) -> None:
        self.dock.set_checked_quietly(self.dock.interactive_button, on)
        self.top_bar.camera_label.setVisible(on)
        self.gestures.set_enabled(on)
        self._keep_overlays_on_top()

    def _on_reactor_state(self, state: str) -> None:
        self.reactor_label.setText(STATE_LABELS.get(state, state.upper()))
        self.reactor_label.setStyleSheet(f"color: {STATE_COLORS.get(state, theme.ACCENT)};")

    # ===================================================================== sending text
    def _on_send(self) -> None:
        text = self.comms.input_line.text().strip()
        if not text or self._busy:
            return
        voice = self._voice_turn
        self._voice_turn = False
        self.comms.input_line.clear()
        self.comms.add_user(text)

        mode = interactive_mode_command(text)
        if mode is not None:  # a UI switch, handled here - never sent to the agent
            self._set_interactive(mode)
            self.comms.add_note(f"Interactive mode {'on' if mode else 'off'}.")
            self.reactor.set_state("idle")
            return

        if compact_command(text):  # makes its own LLM call, so it needs the worker thread
            self._set_busy(True)
            self.reactor.set_state("thinking")
            self.comms.add_note("Compacting older messages…")
            self.compact_requested.emit()
            return

        self._reply = None
        self.mind.begin_request(text, voice=voice)
        short = text if len(text) <= 70 else text[:67] + "…"
        self.reactor_caption.setText(f"“{short}”")
        self._set_busy(True)
        self.reactor.set_state("thinking")
        self.send_requested.emit(text, voice)

    # ============================================================================ voice
    def _start_recording(self) -> None:
        # The global hotkey isn't a widget, so being "disabled" doesn't stop it - check here.
        if self._recording or self._busy:
            return
        self._recording = True
        self.comms.set_recording(True)
        self.reactor.set_state("listening")
        self._recorder.start()

    def _stop_recording(self, *, auto_send: bool) -> None:
        if not self._recording:
            return
        self._recording = False
        self._voice_auto_send = auto_send
        self.comms.set_recording(False)
        self.reactor.set_state("thinking")
        self.transcribe_requested.emit(self._recorder.stop())

    def _on_transcribed(self, text: str) -> None:
        auto_send = self._voice_auto_send
        self._voice_auto_send = False
        self.reactor.set_state("idle")
        if not text:
            return
        self.comms.input_line.setText(text)
        self._voice_turn = True
        if auto_send:
            self._on_send()
        else:
            self.comms.input_line.setFocus()

    # =================================================================== agent events
    def _on_event(self, event: AgentEvent) -> None:
        match event:
            case Thinking():
                pass  # the Mind panel already shows THINKING from the moment we send
            case Token(text=text):
                self.mind.token(text)
                if self._reply is None:
                    self._reply = self.comms.start_reply()
                self._reply.append(text)
            case ToolCall(name=name, args=args):
                self._reply = None
                self.tools_view.set_active(name)
                self.mind.tool_call(name, args)
            case ToolResult(name=name, content=content, status=status):
                self.tools_view.set_active(None)
                self.mind.tool_result(name, content, status)
            case ScreenCaptured(shots=shots):
                self.mind.screen_captured(shots)
            case VisionResult(label=label, text=text, seconds=seconds):
                self.mind.vision(label, text, seconds)
            case Error(message=message):
                self._reply = None
                self.tools_view.set_active(None)
                self.comms.add_error(message)
                self.mind.error(message)
            case ApprovalRequest(name=name, args=args, tier=tier):
                self._reply = None
                self.reactor.set_state("waiting")
                self.mind.approval(name, tier)
                self.approval_view.show_request(name, args, tier)
                self.approval_panel.show()
                self.approval_panel.move_clamped(self.approval_panel.pos())
                self.approval_panel.bring_to_front()

    def _on_approval_decided(self, decision: str) -> None:
        self.approval_panel.hide()
        self.mind.approval_decided(decision)
        self.reactor.set_state("thinking")
        self.resume_requested.emit(decision)

    def _on_turn_done(self) -> None:
        self._reply = None
        self.tools_view.set_active(None)
        self.mind.done()
        self._set_busy(False)
        self.reactor.set_state("idle")

    def _on_compacted(self, message: str) -> None:
        self.comms.add_note(message)
        self._set_busy(False)
        self.reactor.set_state("idle")

    def _on_context_usage(self, used: int, budget: int) -> None:
        self.top_bar.set_context_usage(used, budget)
        self.mind.set_context_usage(used, budget)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.comms.set_busy(busy)

    # ===================================================================== window life
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.gestures.enabled:
            self._set_interactive(False)  # Esc is the always-available way out of camera mode
            return
        super().keyPressEvent(event)

    def bring_to_front(self) -> None:
        """Used by the tray icon to show the window again."""
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self._quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:
        if self.tray is not None and not self._quitting:
            event.ignore()
            self._set_interactive(False)  # never leave the camera on while hidden
            self.hide()
            self.tray.sync_toggle_text()
            self.tray.showMessage(
                "Jarvis",
                "Still running in the tray - right-click the icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            return
        self._set_interactive(False)
        self._vitals_sampler.stop()
        self._hotkey_listener.stop()
        self._thread.quit()
        self._thread.wait()
        super().closeEvent(event)
